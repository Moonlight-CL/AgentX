# AgentX CDK Infrastructure

AWS CDK infrastructure code for deploying AgentX to AWS ECS with supporting services.

## Overview

This CDK project creates a production-ready AWS infrastructure including:

- **ECS Fargate Cluster** - Container orchestration for Backend and Frontend services
- **Application Load Balancer** - Traffic distribution with path-based routing
- **DynamoDB Tables** - 11 tables for multi-tenant data storage
- **Lambda Functions** - Serverless execution for scheduled agent tasks
- **EventBridge Scheduler** - Enterprise-grade task scheduling
- **Bedrock AgentCore Runtime** - AI agent runtime (optional)

## Project Structure

```
cdk/
├── bin/
│   ├── cdk.ts              # Standard CDK entry point (separate stacks)
│   └── cdk-combined.ts     # Combined entry point (all-in-one stack)
├── lib/
│   ├── agentx-stack-combined.ts    # Main stack with all resources
│   ├── agent-schedule-stack.ts     # Schedule/Lambda stack (modular)
│   └── lambda/
│       └── agent-schedule-executor/
│           ├── index.ts            # Lambda handler code
│           ├── package.json
│           └── tsconfig.json
├── deploy.sh               # Automated deployment script
├── package.json
├── cdk.json
└── README.md
```

## Prerequisites

- AWS CLI installed and configured
- Node.js 18.x or later
- AWS CDK v2 (`npm install -g aws-cdk`)
- Docker images pushed to ECR (see main deployment guide)
- Appropriate AWS IAM permissions

## Quick Start

### Using the Deployment Script (Recommended)

```bash
chmod +x deploy.sh

# Basic deployment
./deploy.sh --region us-west-2

# With all options
./deploy.sh --region us-west-2 \
  --vpc-id vpc-12345678 \
  --s3-bucket-name my-agentx-bucket \
  --azure-client-id YOUR_CLIENT_ID \
  --azure-tenant-id YOUR_TENANT_ID \
  --jwt-secret-key YOUR_JWT_SECRET
```

### Manual Deployment

```bash
# Install dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT_ID/REGION

# Deploy
cdk --app "npx ts-node --prefer-ts-exts bin/cdk-combined.ts" deploy AgentXStack
```

## Deployment Options

| Option | Default | Description |
|--------|---------|-------------|
| `--region` | `us-west-2` | AWS region for deployment |
| `--vpc-id` | (creates new) | Use existing VPC ID |
| `--no-dynamodb-tables` | `false` | Skip DynamoDB table creation |
| `--s3-bucket-name` | `agentx-files-bucket` | S3 bucket for file storage |
| `--s3-file-prefix` | `agentx/files` | S3 key prefix for files |
| `--azure-client-id` | - | Azure AD Client ID for SSO |
| `--azure-tenant-id` | - | Azure AD Tenant ID for SSO |
| `--azure-client-secret` | - | Azure AD Client Secret for SSO |
| `--jwt-secret-key` | (generated) | JWT secret for token signing |
| `--service-api-key` | (auto-generated) | API key for Lambda authentication |

## Infrastructure Components

### ECS Services

| Service | Container | Port | CPU | Memory | Tasks |
|---------|-----------|------|-----|--------|-------|
| Backend | `agentx/be` | 8000 | 256 | 512 MB | 2 |
| Frontend | `agentx/fe` | 80 | 256 | 512 MB | 2 |

### Load Balancer Routing

| Path | Target | Port |
|------|--------|------|
| `/api/*` | Backend Service | 8000 |
| `/` (default) | Frontend Service | 80 |

### DynamoDB Tables

| Table | Keys | Purpose |
|-------|------|---------|
| UserTable | `user_id` | User authentication |
| AgentTable | `user_id`, `id` | Agent configurations |
| ChatRecordTable | `user_id`, `id` | Chat sessions |
| ChatResponseTable | `id`, `resp_no` | Chat messages |
| ChatSessionTable | `PK`, `SK` | Session memory |
| HttpMCPTable | `user_id`, `id` | MCP configs |
| RestAPIRegistryTable | `user_id`, `api_id` | REST API configs |
| AgentScheduleTable | `user_id`, `id` | Scheduled tasks |
| OrcheTable | `user_id`, `id` | Orchestrations |
| OrcheExecTable | `user_id`, `id` | Execution history |
| ConfTable | `key` | System config |

### Lambda Functions

**agent-schedule-executor**
- Runtime: Node.js 20.x
- Timeout: 30 seconds
- Purpose: Execute scheduled agent tasks via HTTP call to backend

### Environment Variables

The following environment variables are passed to the Backend container:

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region |
| `S3_BUCKET_NAME` | S3 bucket for file storage |
| `S3_FILE_PREFIX` | S3 key prefix |
| `AZURE_CLIENT_ID` | Azure AD Client ID (optional) |
| `AZURE_TENANT_ID` | Azure AD Tenant ID (optional) |
| `AZURE_CLIENT_SECRET` | Azure AD Client Secret (optional) |
| `JWT_SECRET_KEY` | JWT signing secret |
| `SERVICE_API_KEY` | API key for Lambda auth |
| `LAMBDA_FUNCTION_ARN` | Schedule executor Lambda ARN |
| `SCHEDULE_ROLE_ARN` | EventBridge scheduler role ARN |

## VPC Configuration

### Option 1: New VPC (Default)

Creates a new VPC with:
- 2 Availability Zones
- 1 NAT Gateway
- Public subnets (for ALB)
- Private subnets (for ECS services)

### Option 2: Existing VPC

```bash
./deploy.sh --vpc-id vpc-12345678
```

Requirements:
- Public and private subnets
- Outbound internet access from private subnets
- Proper subnet tagging

## Stack Outputs

| Output | Description |
|--------|-------------|
| `LoadBalancerDNS` | ALB DNS name to access the application |
| `AgentCoreRuntimeArn` | Bedrock AgentCore runtime ARN |
| `AgentScheduleExecutorFunctionArn` | Lambda function ARN |
| `EventBridgeSchedulerRoleArn` | EventBridge scheduler role ARN |

## CDK Commands

```bash
# Compile TypeScript
npm run build

# Watch for changes
npm run watch

# Synthesize CloudFormation template
cdk synth

# Compare changes
cdk diff

# Deploy stack
cdk deploy

# Destroy stack
cdk destroy
```

## Security Notes

- The Backend task role has `AdministratorAccess` for development. Restrict for production.
- Security groups allow traffic only from ALB and between services.
- DynamoDB tables use `user_id` partition keys for data isolation.
- JWT secrets and API keys should be rotated periodically.

## Cost Considerations

- **NAT Gateway**: ~$32/month + data transfer
- **Fargate Tasks**: Based on vCPU and memory usage
- **DynamoDB**: Pay-per-request billing (automatic scaling)
- **ALB**: Fixed hourly cost + LCU usage

Consider:
- VPC endpoints to reduce NAT costs
- Adjusting Fargate task counts based on load
- Reserved capacity for predictable workloads

## Troubleshooting

**CDK bootstrap required**
```bash
cdk bootstrap aws://ACCOUNT_ID/REGION
```

**Lambda build fails**
```bash
cd lib/lambda/agent-schedule-executor
npm install
npm run build
```

**VPC lookup fails**
```bash
# Clear CDK context cache
rm cdk.context.json
cdk synth
```

**Permission denied**
Ensure your AWS credentials have permissions for:
- CloudFormation
- ECS, ECR
- DynamoDB
- Lambda, EventBridge
- IAM role creation
- VPC (if creating new)

## Related Documentation

- [Main Deployment Guide](../README-DEPLOYMENT.md)
- [Backend Documentation](../be/README.md)
- [Frontend Documentation](../fe/README.md)
