# AgentX EKS Deployment Guide

## Architecture Overview

```
                    Internet
                       |
                  [AWS ALB] (HTTPS:443, idle_timeout=900s)
                   /       \
          /api/*  /         \  /*
         v                   v
  [Backend Service]    [Frontend Service]
   FastAPI:8000         Nginx:80 (SPA)
        |
   +---------+----------+-----------+
   |         |          |           |
 [RDS PG] [Bedrock] [S3 Bucket] [EventBridge]
                                     |
                                 [Lambda]
                                     |
                              POST /api/agent/async_chat
```

**Components:**
- **Backend**: FastAPI (Python 3.13), port 8000, SSE streaming
- **Frontend**: React SPA (Vite + Bun) served via Nginx, port 80
- **Storage**: Amazon RDS PostgreSQL
- **LLM**: Amazon Bedrock
- **File Storage**: Amazon S3
- **Scheduled Tasks**: EventBridge Scheduler + Lambda -> Backend async_chat API
- **Auth**: JWT + Azure AD SSO (optional)

---

## Prerequisites

- AWS CLI configured with appropriate permissions
- `kubectl` installed and configured
- `eksctl` installed
- Docker with BuildKit support (for ARM64 builds)
- Node.js (for Lambda build)

---

## Step 1: VPC and Networking

Use an existing VPC or create one with 2-3 Availability Zones:
- **Public subnets**: ALB, NAT Gateway
- **Private subnets**: EKS nodes, RDS

Tag subnets for ALB Controller auto-discovery:

```bash
# Public subnets
aws ec2 create-tags --resources subnet-xxx --tags Key=kubernetes.io/role/elb,Value=1

# Private subnets
aws ec2 create-tags --resources subnet-yyy --tags Key=kubernetes.io/role/internal-elb,Value=1

# All subnets
aws ec2 create-tags --resources subnet-xxx subnet-yyy --tags Key=kubernetes.io/cluster/agentx-cluster,Value=shared
```

---

## Step 2: Create EKS Cluster

```bash
eksctl create cluster \
  --name agentx-cluster \
  --region us-west-2 \
  --version 1.31 \
  --vpc-private-subnets=subnet-xxx,subnet-yyy \
  --vpc-public-subnets=subnet-aaa,subnet-bbb \
  --without-nodegroup
```

Enable OIDC provider (required for IRSA):

```bash
eksctl utils associate-iam-oidc-provider --cluster agentx-cluster --approve
```

---

## Step 3: Create Managed Node Group

```bash
eksctl create nodegroup \
  --cluster agentx-cluster \
  --name agentx-ng \
  --node-type m7g.xlarge \
  --nodes 3 --nodes-min 2 --nodes-max 6 \
  --node-ami-family AmazonLinux2023 \
  --node-private-networking
```

> **Note**: Must use **Graviton instances** (m7g/c7g/r7g) to match the ARM64 Docker images built by `build-and-push.sh`.

---

## Step 4: Create Amazon RDS PostgreSQL

| Setting | Value |
|---------|-------|
| Engine | PostgreSQL 16 |
| Instance | `db.r7g.large` (prod) / `db.t4g.medium` (dev) |
| DB Name | `agentx` |
| VPC | Same as EKS, private subnets only |
| Security Group | Allow port 5432 from EKS node security group only |
| Multi-AZ | Yes (prod) / No (dev) |
| Encryption | Enabled |
| max_connections | >= 200 |

Note the RDS endpoint for later use in `DATABASE_URL`.

---

## Step 5: Create S3 Bucket

```bash
aws s3 mb s3://your-agentx-bucket --region us-west-2
aws s3api put-public-access-block --bucket your-agentx-bucket \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

## Step 6: Install AWS Load Balancer Controller

### 6.1 Create IAM Policy

```bash
curl -o /tmp/iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.1/docs/install/iam_policy.json
```

> **Important**: The official policy may be missing newer actions. Ensure the policy includes:
> - `elasticloadbalancing:DescribeListenerAttributes`
> - `elasticloadbalancing:ModifyListenerAttributes`
>
> Add them manually if not present.

```bash
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file:///tmp/iam_policy.json
```

### 6.2 Create ServiceAccount with IRSA

```bash
eksctl create iamserviceaccount \
  --cluster=agentx-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve
```

### 6.3 Install Controller

Follow the [official installation guide](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/deploy/installation/) using YAML manifests or Helm.

---

## Step 7: Configure IRSA for Backend

### 7.1 Create IAM Policy

Create `AgentXBackendPolicy` with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:HeadObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-agentx-bucket",
        "arn:aws:s3:::your-agentx-bucket/*"
      ]
    },
    {
      "Sid": "EventBridgeScheduler",
      "Effect": "Allow",
      "Action": [
        "scheduler:CreateSchedule",
        "scheduler:UpdateSchedule",
        "scheduler:DeleteSchedule",
        "scheduler:GetSchedule"
      ],
      "Resource": "arn:aws:scheduler:*:*:schedule/default/agent-schedule-*"
    },
    {
      "Sid": "PassRoleForScheduler",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::<ACCOUNT_ID>:role/agentx-eventbridge-scheduler-role",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "scheduler.amazonaws.com"
        }
      }
    }
  ]
}
```

### 7.2 Create IRSA Role

```bash
eksctl create iamserviceaccount \
  --name agentx-backend-sa \
  --namespace agentx \
  --cluster agentx-cluster \
  --attach-policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/AgentXBackendPolicy \
  --approve \
  --override-existing-serviceaccounts
```

Or manually create the role with trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.eks.<REGION>.amazonaws.com/id/<OIDC_ID>"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.<REGION>.amazonaws.com/id/<OIDC_ID>:sub": "system:serviceaccount:agentx:agentx-backend-sa",
        "oidc.eks.<REGION>.amazonaws.com/id/<OIDC_ID>:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

Update `k8s/base/backend/serviceaccount.yaml` with the role ARN:

```yaml
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::<ACCOUNT_ID>:role/agentx-backend-irsa-role
```

> **Note**: With IRSA, backend pods **do not need** `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` environment variables.

---

## Step 8: Request ACM Certificate

```bash
aws acm request-certificate \
  --domain-name "agentx-eks.your-domain.com" \
  --validation-method DNS \
  --region us-west-2
```

Complete DNS validation and note the certificate ARN. Update `k8s/base/ingress/ingress.yaml`:

```yaml
alb.ingress.kubernetes.io/certificate-arn: "<ACM_CERTIFICATE_ARN>"
```

---

## Step 9: Deploy Lambda (Scheduled Tasks)

The Lambda function is the bridge between EventBridge Scheduler and the backend `async_chat` API.

```
EventBridge Scheduler -> Lambda -> POST /api/agent/async_chat (with X-API-Key)
```

### 9.1 Deploy

```bash
cd lambda
./deploy-lambda.sh <aws-region> <api-endpoint> <service-api-key>

# Example:
./deploy-lambda.sh us-west-2 https://agentx-eks.your-domain.com/api/agent/async_chat your-service-api-key
```

The script will:
1. Build TypeScript source (`npm install && tsc`)
2. Package and upload Lambda (Node.js 20.x, ARM64, 30s timeout)
3. Create Lambda execution role (CloudWatch Logs)
4. Create EventBridge Scheduler role (lambda:InvokeFunction)

### 9.2 Note the Output ARNs

```
LAMBDA_FUNCTION_ARN=arn:aws:lambda:<region>:<account>:function:agentx-schedule-executor
SCHEDULE_ROLE_ARN=arn:aws:iam::<account>:role/agentx-eventbridge-scheduler-role
```

These go into `k8s/base/secrets/secrets.yaml`.

---

## Step 10: Configure K8s Secrets

Edit `k8s/base/secrets/secrets.yaml` with actual values:

```yaml
stringData:
  JWT_SECRET_KEY: "<your-jwt-secret>"
  DATABASE_URL: "postgresql://<user>:<password>@<rds-endpoint>:5432/agentx"
  SERVICE_API_KEY: "<your-service-api-key>"
  LAMBDA_FUNCTION_ARN: "arn:aws:lambda:<region>:<account>:function:agentx-schedule-executor"
  SCHEDULE_ROLE_ARN: "arn:aws:iam::<account>:role/agentx-eventbridge-scheduler-role"
  # Optional: Azure AD SSO
  AZURE_CLIENT_ID: ""
  AZURE_TENANT_ID: ""
  AZURE_CLIENT_SECRET: ""
```

> **Production recommendation**: Use [External Secrets Operator](https://external-secrets.io/) with AWS Secrets Manager instead of plaintext secrets in YAML.

---

## Step 11: Build and Push Docker Images

```bash
# Build with version tag (defaults to git short SHA)
./build-and-push.sh us-west-2 <ACCOUNT_ID> v1.0.0

# Or use default tag:
./build-and-push.sh us-west-2
```

This builds ARM64 images and pushes to ECR:
- `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/agentx/be:<tag>`
- `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/agentx/fe:<tag>`

---

## Step 12: Update Image References in Overlays

Edit `k8s/overlays/dev/kustomization.yaml` (or `prod`):

```yaml
images:
  - name: agentx/be
    newName: <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/agentx/be
    newTag: v1.0.0
  - name: agentx/fe
    newName: <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/agentx/fe
    newTag: v1.0.0
```

---

## Step 13: Deploy to EKS

```bash
# Dev environment
kubectl apply -k k8s/overlays/dev

# Production environment
kubectl apply -k k8s/overlays/prod
```

---

## Step 14: Configure DNS

After the Ingress is created, get the ALB address:

```bash
kubectl get ingress -n agentx
# NAME             CLASS   HOSTS                       ADDRESS
# agentx-ingress   alb     agentx-eks.your-domain.com  k8s-agentx-xxxxx.us-west-2.elb.amazonaws.com
```

Add a CNAME record in Route 53 (or your DNS provider):

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "agentx-eks.your-domain.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<ALB_ADDRESS>"}]
      }
    }]
  }'
```

---

## Step 15: Verify Deployment

```bash
# 1. Check pods
kubectl get pods -n agentx
# agentx-backend-xxx    1/1   Running
# agentx-backend-xxx    1/1   Running
# agentx-frontend-xxx   1/1   Running

# 2. Check services
kubectl get svc -n agentx

# 3. Check ingress
kubectl get ingress -n agentx

# 4. Test health check
curl https://agentx-eks.your-domain.com/ping
# {"status":"healthy","service":"AgentX-BE"}

# 5. Test frontend
curl -s -o /dev/null -w "%{http_code}" https://agentx-eks.your-domain.com/
# 200

# 6. Test Lambda -> Backend integration
aws lambda invoke --function-name agentx-schedule-executor --region us-west-2 \
  --payload '{"user_id":"test","agent_id":"test","agent_owner_id":"test","schedule_id":"test"}' \
  --cli-binary-format raw-in-base64-out /tmp/lambda-out.json && cat /tmp/lambda-out.json
```

---

## Directory Structure

```
k8s/
├── base/
│   ├── kustomization.yaml              # Base Kustomize config
│   ├── namespace.yaml                  # agentx namespace
│   ├── backend/
│   │   ├── serviceaccount.yaml         # IRSA annotation
│   │   ├── configmap.yaml              # APP_ENV, STORAGE_BACKEND, AWS_REGION, S3
│   │   ├── deployment.yaml             # 3 replicas, health probes, preStop
│   │   ├── service.yaml                # ClusterIP:8000
│   │   └── hpa.yaml                    # 3-10 replicas, CPU 70%
│   ├── frontend/
│   │   ├── configmap.yaml              # Azure AD runtime vars
│   │   ├── deployment.yaml             # 2 replicas, Nginx:80
│   │   ├── service.yaml                # ClusterIP:80
│   │   └── hpa.yaml                    # 2-5 replicas
│   ├── secrets/
│   │   └── secrets.yaml                # JWT, DATABASE_URL, API keys, ARNs
│   ├── ingress/
│   │   └── ingress.yaml                # ALB, path routing, SSL, idle_timeout=900s
│   └── network-policies/
│       ├── backend-netpol.yaml         # Ingress 8000, Egress PG/HTTPS/DNS
│       └── frontend-netpol.yaml        # Ingress 80, Egress DNS only
└── overlays/
    ├── dev/
    │   └── kustomization.yaml          # Low replicas/resources, dev image tags
    └── prod/
        └── kustomization.yaml          # High resources, semver tags, WAF

lambda/
├── deploy-lambda.sh                    # One-click Lambda deployment
└── agent-schedule-executor/
    ├── index.ts                        # EventBridge -> async_chat handler
    ├── package.json
    └── tsconfig.json
```

---

## Key Design Decisions

### SSE Streaming

The ALB idle timeout is set to **900 seconds** (`idle_timeout.timeout_seconds=900`) to support long-running LLM inference via SSE. The default 60s would prematurely terminate streaming connections.

Backend deployment uses `terminationGracePeriodSeconds: 120` and `preStop: sleep 15` to gracefully drain SSE connections during rolling updates.

### Path Routing

When `APP_ENV=production`, the backend registers all routes under `/api/*` prefix. The ALB forwards `/api/*` to the backend **without path rewriting**. All other paths (`/*`) go to the frontend Nginx, which serves the SPA via `try_files $uri $uri/ /index.html`.

### PG Connection Pool Sizing

`pg_config.py` configures `ThreadedConnectionPool(minconn=2, maxconn=10)`. With HPA `maxReplicas=10`, maximum concurrent connections = **100**. RDS `max_connections` should be >= 120.

### IRSA (IAM Roles for Service Accounts)

Backend pods access AWS services (Bedrock, S3, EventBridge) via IRSA — **no AWS access keys** in environment variables. The ServiceAccount annotation injects temporary credentials automatically.

### Schema Migration

`db_init.py` runs `CREATE TABLE IF NOT EXISTS` on every pod startup. This is idempotent and safe for concurrent pod startups. For complex future migrations, use a K8s Job.

---

## Troubleshooting

### Pods in CrashLoopBackOff

```bash
kubectl logs <pod-name> -n agentx --tail=50
```

Common causes:
- Missing `db/schema.sql` in Docker image → Ensure `COPY db/ ./db/` in `be/Dockerfile`
- `DATABASE_URL` incorrect or RDS unreachable → Check security group rules
- IRSA role not found → Verify `agentx-backend-irsa-role` exists with correct trust policy

### Ingress ADDRESS Empty

```bash
kubectl describe ingress agentx-ingress -n agentx | grep -A5 Events
```

Common causes:
- ALB Controller not installed → `kubectl get deploy -n kube-system | grep load-balancer`
- IAM permissions insufficient → Check controller logs: `kubectl logs deploy/aws-load-balancer-controller -n kube-system --tail=20`
- Missing `DescribeListenerAttributes` action → Update IAM policy

### New Image Not Pulled

Deployments use `imagePullPolicy: Always`. If still using cached images:

```bash
kubectl rollout restart deployment/agentx-backend -n agentx
```

### IRSA Not Working

```bash
# Verify IRSA env vars injected
kubectl exec -n agentx deploy/agentx-backend -- env | grep AWS_

# Expected:
# AWS_ROLE_ARN=arn:aws:iam::<ACCOUNT>:role/agentx-backend-irsa-role
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
```

If missing, the role trust policy is likely misconfigured. Verify the OIDC provider URL, namespace, and service account name match.

### Lambda Schedule Not Triggering

```bash
# Check Lambda logs
aws logs tail /aws/lambda/agentx-schedule-executor --follow --region us-west-2

# Test Lambda manually
aws lambda invoke --function-name agentx-schedule-executor --region us-west-2 \
  --payload '{"user_id":"test","agent_id":"test","agent_owner_id":"test","schedule_id":"test"}' \
  --cli-binary-format raw-in-base64-out /tmp/out.json && cat /tmp/out.json
```

Common causes:
- `API_ENDPOINT` wrong → Check Lambda environment variables
- `SERVICE_API_KEY` mismatch → Must match backend's `SERVICE_API_KEY`
- EventBridge Scheduler role missing `lambda:InvokeFunction` permission

---

## Reusing an Existing ALB (IngressGroup)

If you already have an ALB created by the AWS Load Balancer Controller, AgentX can share it instead of creating a new one. This is done via the **IngressGroup** mechanism.

### How It Works

ALB Controller uses the `alb.ingress.kubernetes.io/group.name` annotation to determine which Ingress resources share the same ALB. Ingress resources with the **same `group.name`** are merged into a single ALB as separate listener rules.

By default, AgentX uses `group.name: agentx`, which creates a **dedicated ALB**. To share an existing ALB, change this to match the existing group name.

### Step 1: Find the Existing Group Name

```bash
kubectl get ingress --all-namespaces \
  -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.metadata.annotations.alb\.ingress\.kubernetes\.io/group\.name}{"\n"}{end}'
```

### Step 2: Patch in Overlay

Add the following patch to your overlay `kustomization.yaml` (e.g., `k8s/overlays/dev/kustomization.yaml`):

```yaml
# Reuse existing ALB by joining its IngressGroup
- target:
    kind: Ingress
    name: agentx-ingress
  patch: |
    - op: replace
      path: /metadata/annotations/alb.ingress.kubernetes.io~1group.name
      value: "shared-alb"
    - op: replace
      path: /metadata/annotations/alb.ingress.kubernetes.io~1group.order
      value: "10"
```

Replace `shared-alb` with the actual group name from Step 1. The `group.order` controls rule priority (lower number = higher priority) — choose a value that doesn't conflict with existing rules.

### Important Considerations

| Concern | Detail |
|---------|--------|
| **idle_timeout=900s** | This is an ALB-level setting. If AgentX sets it, it applies to **all services** sharing the ALB. If other services can't tolerate 900s idle timeout, keep AgentX on a separate ALB. |
| **ALB-level annotations** | `scheme`, `certificate-arn`, `load-balancer-attributes` etc. are shared across the group. The first Ingress in the group sets these; others should be consistent or omit them. |
| **SSL certificates** | A shared ALB supports multiple ACM certificates via SNI. Use comma-separated ARNs: `"arn:...cert1,arn:...cert2"` |
| **Host-based isolation** | AgentX uses its own domain in the `host` field, so routing rules won't conflict with other services on the same ALB. |
| **When NOT to share** | If your SSE streaming requires 900s idle timeout and other services need the default 60s, use a separate ALB (the default `group.name: agentx` configuration). |

---

## Updating the Application

```bash
# 1. Build and push new images
./build-and-push.sh us-west-2 <ACCOUNT_ID> v1.1.0

# 2. Update image tag in overlay
cd k8s/overlays/dev
kustomize edit set image agentx/be=<ECR>/agentx/be:v1.1.0
kustomize edit set image agentx/fe=<ECR>/agentx/fe:v1.1.0

# 3. Apply (zero-downtime rolling update)
kubectl apply -k .

# 4. Monitor rollout
kubectl rollout status deployment/agentx-backend -n agentx

# 5. Update Lambda if needed
cd lambda
./deploy-lambda.sh us-west-2 https://agentx-eks.your-domain.com/api/agent/async_chat <api-key>
```
