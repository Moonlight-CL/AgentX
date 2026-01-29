# AgentX AWS Deployment Guide

Complete guide for deploying AgentX to AWS using Docker containers and AWS CDK.

## Architecture Overview

```
                                    ┌─────────────────────────────┐
                                    │         Internet            │
                                    └──────────────┬──────────────┘
                                                   │
                                    ┌──────────────▼──────────────┐
                                    │  Application Load Balancer   │
                                    │      (HTTP/HTTPS)            │
                                    └──────────────┬──────────────┘
                                                   │
                         ┌─────────────────────────┴─────────────────────────┐
                         │                                                    │
               ┌─────────▼─────────┐                            ┌────────────▼────────────┐
               │   /api/* → BE     │                            │      / → FE (default)   │
               └─────────┬─────────┘                            └────────────┬────────────┘
                         │                                                    │
        ┌────────────────▼────────────────┐              ┌───────────────────▼───────────────┐
        │    Backend Service (ECS)         │              │      Frontend Service (ECS)       │
        │    Container: agentx/be          │              │      Container: agentx/fe         │
        │    Port: 8000                    │              │      Port: 80                     │
        │    Tasks: 2 (scalable)           │              │      Tasks: 2 (scalable)          │
        └────────────────┬────────────────┘              └───────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┬─────────────────────┬──────────────────────┐
    ▼                    ▼                    ▼                     ▼                      ▼
┌─────────┐      ┌─────────────┐      ┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│DynamoDB │      │ EventBridge │      │   Lambda    │      │   Bedrock    │      │    S3       │
│(11 Tables)│    │  Scheduler  │      │  Functions  │      │  AgentCore   │      │  Storage    │
└─────────┘      └─────────────┘      └─────────────┘      └──────────────┘      └─────────────┘
```

## Deployable Components

| Component | Container | Port | Path | Description |
|-----------|-----------|------|------|-------------|
| Backend | `agentx/be` | 8000 | `/api/*` | FastAPI application with agent logic |
| Frontend | `agentx/fe` | 80 | `/` | React SPA for user interface |
| AgentCore Runtime | `agentx/rt-agentcore` | - | - | Bedrock AgentCore runtime (optional) |

## Prerequisites

- AWS CLI installed and configured with appropriate permissions
- Docker installed and running
- Node.js 18.x or later
- AWS CDK v2 (`npm install -g aws-cdk`)
- Sufficient AWS permissions for ECS, ECR, DynamoDB, Lambda, EventBridge, IAM

## Deployment Steps

### Step 1: Create ECR Repositories

Create the ECR repositories to store Docker images:

```bash
# Set environment variables
export AWS_REGION=us-west-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create repositories
aws ecr create-repository --repository-name agentx/be --region $AWS_REGION
aws ecr create-repository --repository-name agentx/fe --region $AWS_REGION
aws ecr create-repository --repository-name agentx/rt-agentcore --region $AWS_REGION
```

### Step 2: Build and Push Docker Images

#### Option A: Automated Script (Recommended)

```bash
chmod +x build-and-push.sh
./build-and-push.sh us-west-2
```

#### Option B: Manual Build

```bash
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Backend
cd be
docker build --platform linux/amd64 -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/be:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/be:latest

# Build and push AgentCore Runtime (ARM64)
docker buildx build --platform linux/arm64 -f ./Dockerfile.agentcore \
  -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/rt-agentcore:latest --load .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/rt-agentcore:latest

# Build and push Frontend
cd ../fe
docker build --platform linux/amd64 -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/fe:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/fe:latest
```

### Step 3: Deploy Infrastructure with CDK

#### Option A: Automated Deploy Script (Recommended)

```bash
cd cdk
chmod +x deploy.sh

# Basic deployment (creates new VPC and DynamoDB tables)
./deploy.sh --region us-west-2

# Full deployment with all options
./deploy.sh --region us-west-2 \
  --vpc-id vpc-12345678 \
  --s3-bucket-name my-agentx-bucket \
  --azure-client-id YOUR_AZURE_CLIENT_ID \
  --azure-tenant-id YOUR_AZURE_TENANT_ID \
  --azure-client-secret YOUR_AZURE_SECRET \
  --jwt-secret-key YOUR_JWT_SECRET \
  --service-api-key YOUR_SERVICE_API_KEY
```

#### Option B: Manual CDK Deployment

```bash
cd cdk
npm install

# Bootstrap CDK (first time only)
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION

# Deploy the stack
cdk --app "npx ts-node --prefer-ts-exts bin/cdk-combined.ts" deploy AgentXStack \
  -c vpcId=vpc-12345678 \
  -c s3BucketName=my-bucket \
  -c createDynamoDBTables=true
```

## Deployment Options Reference

| Option | Default | Description |
|--------|---------|-------------|
| `--region` | `us-west-2` | AWS region for deployment |
| `--vpc-id` | (creates new) | Use existing VPC instead of creating new one |
| `--no-dynamodb-tables` | `false` | Skip DynamoDB table creation |
| `--s3-bucket-name` | `agentx-files-bucket` | S3 bucket for file storage |
| `--s3-file-prefix` | `agentx/files` | S3 path prefix for files |
| `--azure-client-id` | - | Azure AD Client ID (for SSO) |
| `--azure-tenant-id` | - | Azure AD Tenant ID (for SSO) |
| `--azure-client-secret` | - | Azure AD Client Secret (for SSO) |
| `--jwt-secret-key` | (generated) | JWT secret for token signing |
| `--service-api-key` | (auto-generated) | API key for Lambda authentication |

## DynamoDB Tables

The deployment creates 11 DynamoDB tables for data storage:

### Core Tables

| Table | Partition Key | Sort Key | Purpose |
|-------|---------------|----------|---------|
| UserTable | `user_id` (S) | - | User authentication (passwords, profile) |
| AgentTable | `user_id` (S) | `id` (S) | Agent configurations |
| ChatRecordTable | `user_id` (S) | `id` (S) | Chat session metadata |
| ChatResponseTable | `id` (S) | `resp_no` (N) | Individual chat messages |
| ChatSessionTable | `PK` (S) | `SK` (S) | Session memory storage |

### Feature Tables

| Table | Partition Key | Sort Key | Purpose |
|-------|---------------|----------|---------|
| HttpMCPTable | `user_id` (S) | `id` (S) | MCP server configurations |
| RestAPIRegistryTable | `user_id` (S) | `api_id` (S) | REST API adapter configs |
| AgentScheduleTable | `user_id` (S) | `id` (S) | Scheduled task definitions |
| OrcheTable | `user_id` (S) | `id` (S) | Orchestration workflows |
| OrcheExecTable | `user_id` (S) | `id` (S) | Workflow execution history |
| ConfTable | `key` (S) | - | System-wide configurations |

> All tables use PAY_PER_REQUEST billing mode for automatic scaling.

## VPC Configuration

### Option 1: New VPC (Default)

When no VPC ID is provided, CDK creates a new VPC with:
- 2 Availability Zones for high availability
- 1 NAT Gateway for outbound internet access
- Public subnets for ALB
- Private subnets for ECS services

### Option 2: Existing VPC

To use an existing VPC:

```bash
./deploy.sh --region us-west-2 --vpc-id vpc-12345678
```

**Requirements for existing VPC:**
- Must have both public and private subnets
- Private subnets must have outbound internet connectivity (NAT Gateway or similar)
- Subnets must be properly tagged for ECS and ALB

## CloudFormation Outputs

After successful deployment, the stack outputs:

| Output | Description |
|--------|-------------|
| `LoadBalancerDNS` | ALB DNS name to access the application |
| `AgentCoreRuntimeArn` | ARN of Bedrock AgentCore runtime |
| `AgentScheduleExecutorFunctionArn` | Lambda function ARN for scheduling |
| `EventBridgeSchedulerRoleArn` | IAM role ARN for EventBridge |

## Post-Deployment Verification

### 1. Check Stack Status

```bash
aws cloudformation describe-stacks --stack-name AgentXStack --query 'Stacks[0].StackStatus'
```

### 2. Get Application URL

```bash
aws cloudformation describe-stacks --stack-name AgentXStack \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text
```

### 3. Verify ECS Services

```bash
aws ecs list-services --cluster agentx-cluster --region us-west-2
aws ecs describe-services --cluster agentx-cluster \
  --services agentx-be-service agentx-fe-service --region us-west-2
```

### 4. Check Service Health

```bash
# Get ALB DNS
ALB_DNS=$(aws cloudformation describe-stacks --stack-name AgentXStack \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text)

# Test backend health
curl http://$ALB_DNS/api/health

# Access frontend
echo "Application URL: http://$ALB_DNS"
```

### 5. Test User Registration

1. Open `http://<ALB_DNS>` in your browser
2. Click "Register" to create a new account
3. Log in with your credentials
4. Verify you can create and interact with agents

### 6. Test Azure AD SSO (if configured)

1. Click "Sign in with Microsoft" on the login page
2. Authenticate with Azure AD credentials
3. Verify automatic user provisioning
4. Test logout and re-login

## Production Recommendations

### SSL/TLS Certificate

For production, add an SSL certificate to the ALB:

1. Request a certificate in AWS Certificate Manager (ACM)
2. Associate the certificate with the ALB HTTPS listener
3. Update security groups to allow HTTPS (443)

### Security Hardening

- Review and restrict IAM policies (remove AdministratorAccess)
- Enable VPC Flow Logs for network monitoring
- Use AWS Secrets Manager for sensitive configuration
- Enable CloudWatch alarms for service monitoring
- Consider enabling AWS WAF for web application protection

### Cost Optimization

- Adjust ECS task counts based on traffic patterns
- Consider using EC2 Spot instances for non-critical workloads
- Use VPC endpoints for AWS service access to reduce NAT costs
- Enable DynamoDB auto-scaling for variable workloads

## Troubleshooting

### Common Issues

**Images not found in ECR**
```bash
# Verify images exist
aws ecr describe-images --repository-name agentx/be --region us-west-2
aws ecr describe-images --repository-name agentx/fe --region us-west-2
```

**ECS tasks failing to start**
```bash
# Check task logs
aws logs get-log-events --log-group-name /ecs/agentx-be \
  --log-stream-name <stream-name> --region us-west-2
```

**CDK bootstrap required**
```bash
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION
```

**VPC subnets not found**
```bash
# Verify VPC has proper subnets
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-12345678" --region us-west-2
```

### Logs and Monitoring

- **Backend logs**: CloudWatch Log Group `/ecs/agentx-be`
- **Frontend logs**: CloudWatch Log Group `/ecs/agentx-fe`
- **Lambda logs**: CloudWatch Log Group `/aws/lambda/agent-schedule-executor`

## Cleanup

To delete all deployed resources:

```bash
cd cdk
cdk destroy AgentXStack
```

> DynamoDB tables with data will require manual deletion to prevent accidental data loss.
