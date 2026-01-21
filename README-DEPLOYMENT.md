# AgentX Deployment Guide

A comprehensive guide for deploying the AgentX platform to AWS using Docker and AWS CDK.

## 🏗️ Architecture Overview

The AgentX deployment architecture consists of:

- **AWS ECS Cluster**: Container orchestration service
- **AWS ECR Repositories**: Docker image storage
- **Application Load Balancer**: Traffic distribution
- **DynamoDB Tables**: Data storage with user authentication and data isolation
- **EventBridge Scheduler**: Task scheduling
- **Lambda Functions**: Serverless execution

## 🧩 Components

The project consists of the following deployable components:

1. **Backend (BE)**: FastAPI Python application
   - Container: `agentx/be`
   - Port: 8000
   - Path: `/api/*`

2. **Frontend (FE)**: React/TypeScript application
   - Container: `agentx/fe`
   - Port: 80
   - Path: `/` (default)

3. **MySQL MCP Server**: MySQL Model Context Protocol server
   - Container: `agentx/mcp-mysql`
   - Port: 3000
   - Path: `/mcp-server/mysql/*`

4. **Redshift MCP Server**: Redshift Model Context Protocol server
   - Container: `agentx/mcp-redshift`
   - Port: 3000
   - Path: `/mcp-server/redshift/*`

5. **DuckDB MCP Server**: DuckDB Model Context Protocol server
   - Container: `agentx/mcp-duckdb`
   - Port: 8000
   - Path: `/mcp-server/duckdb/*`

6. **OpenSearch MCP Server**: OpenSearch Model Context Protocol server
   - Container: `agentx/mcp-opensearch`
   - Port: 3000
   - Path: `/mcp-server/opensearch/*`

## 🚀 Deployment Steps

### 1. Prerequisites

- AWS CLI installed and configured
- Docker installed
- Node.js 18.x or later
- AWS CDK v2 installed (`npm install -g aws-cdk`)
- AWS account with appropriate permissions

### 2. Complete Deployment Process

The deployment process consists of three main steps:

1. **Create ECR repositories** for storing Docker images
2. **Build and push Docker images** to ECR
3. **Deploy the infrastructure** using AWS CDK

#### Step 1: Create ECR Repositories

Before building and pushing Docker images, you need to create ECR repositories:

```bash
# Set your AWS region
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create ECR repositories
aws ecr create-repository --repository-name agentx/be --region $AWS_REGION
aws ecr create-repository --repository-name agentx/rt-agentcore --region $AWS_REGION
aws ecr create-repository --repository-name agentx/fe --region $AWS_REGION
aws ecr create-repository --repository-name agentx/mcp-mysql --region $AWS_REGION
aws ecr create-repository --repository-name agentx/mcp-redshift --region $AWS_REGION
aws ecr create-repository --repository-name agentx/mcp-duckdb --region $AWS_REGION
aws ecr create-repository --repository-name agentx/mcp-opensearch --region $AWS_REGION
```

#### Step 2: Build and Push Docker Images

After creating the repositories, build and push the Docker images:

##### Option A: Using the Automated Script (Recommended)

```bash
# Make the script executable
chmod +x build-and-push.sh

# Run the script with your AWS region
./build-and-push.sh us-west-2
```

This script will:
1. Log in to your AWS ECR registry
2. Create ECR repositories if they don't exist
3. Build Docker images for all components
4. Tag and push the images to ECR

##### Option B: Manual Build and Push

```bash
# Set your AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-west-2

# Log in to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create repositories if they don't exist
aws ecr describe-repositories --repository-names agentx/be --region $AWS_REGION || aws ecr create-repository --repository-name agentx/be --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/rt-agentcore --region $AWS_REGION || aws ecr create-repository --repository-name agentx/rt-agentcore --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/fe --region $AWS_REGION || aws ecr create-repository --repository-name agentx/fe --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/mcp-mysql --region $AWS_REGION || aws ecr create-repository --repository-name agentx/mcp-mysql --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/mcp-redshift --region $AWS_REGION || aws ecr create-repository --repository-name agentx/mcp-redshift --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/mcp-duckdb --region $AWS_REGION || aws ecr create-repository --repository-name agentx/mcp-duckdb --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/mcp-opensearch --region $AWS_REGION || aws ecr create-repository --repository-name agentx/mcp-opensearch --region $AWS_REGION

# Build and push backend and agentcore runtime image
cd be
docker build --platform linux/amd64 -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/be:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/be:latest

docker buildx build --platform linux/arm64 -f ./Dockerfile.agentcore -t $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/agentx/rt-agentcore:latest  --load .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/rt-agentcore:latest

# Build and push frontend
cd ../fe
docker build --platform linux/amd64 -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/fe:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/fe:latest

# Build and push MySQL MCP server
cd ../mcp/mysql
docker build --platform linux/amd64 -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/mcp-mysql:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/mcp-mysql:latest

# Build and push Redshift MCP server
cd ../mcp/redshift
docker build --platform linux/amd64 -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/mcp-redshift:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/mcp-redshift:latest

```

#### Step 3: Deploy with CDK

After pushing the Docker images to ECR, deploy the infrastructure using AWS CDK:

##### Option A: Using the Automated Script (Recommended)

```bash
# Make the script executable
chmod +x cdk/deploy.sh

# Navigate to the CDK directory
cd cdk

# Deployment with Azure AD SSO and existing VPC (no MCP servers)
./deploy.sh --region us-west-2 \
  --vpc-id vpc-12345678 \
  --no-mysql-mcp \
  --no-redshift-mcp \
  --no-duckdb-mcp \
  --no-opensearch-mcp \
  --no-aws-db-mcp \
  --azure-client-id your-azure-client-id \
  --azure-tenant-id your-azure-tenant-id \
  --azure-client-secret your-azure-client-secret \
  --jwt-secret-key your-secure-jwt-secret \
  --s3-bucket-name your-s3-bucket
```

Available options:
- `--region REGION`: AWS region to deploy to (default: from AWS config or us-west-2)
- `--vpc-id VPC_ID`: Use existing VPC ID instead of creating a new one
- `--no-mysql-mcp`: Disable MySQL MCP server deployment
- `--no-redshift-mcp`: Disable Redshift MCP server deployment
- `--no-duckdb-mcp`: Disable DuckDB MCP server deployment
- `--no-opensearch-mcp`: Disable OpenSearch MCP server deployment
- `--no-aws-db-mcp`: Disable AWS DB MCP server deployment
- `--aws-db-mcp-cpu CPU`: CPU units for AWS DB MCP server (256, 512, 1024, 2048, 4096, default: 1024)
- `--aws-db-mcp-memory MEMORY`: Memory in MiB for AWS DB MCP server (default: 2048)
- `--no-dynamodb-tables`: Disable creation of DynamoDB tables for agent and MCP services
- `--s3-bucket-name BUCKET`: S3 bucket name for file storage (default: agentx-files-bucket)
- `--s3-file-prefix PREFIX`: S3 file prefix for file storage (default: agentx/files)
- `--azure-client-id ID`: Azure AD Client ID for SSO (optional)
- `--azure-tenant-id ID`: Azure AD Tenant ID for SSO (optional)
- `--azure-client-secret SEC`: Azure AD Client Secret for SSO (optional)
- `--jwt-secret-key KEY`: JWT Secret Key for token generation (optional, uses default if not provided)
- `--help`: Display help message with all available options

##### Option B: Manual CDK Deployment

```bash
# Navigate to the CDK directory
cd cdk

# Install dependencies
npm install

# Bootstrap CDK (if not already done)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-west-2
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION

# Deploy the stacks
cdk --app "npx ts-node --prefer-ts-exts bin/cdk-combined.ts" deploy AgentXStack
```

### 3. DynamoDB Tables Structure

The CDK deployment creates the following DynamoDB tables with user authentication and data isolation support:

**Core Tables:**

#### UserTable (User authentication and management)
- **Partition Key**: `user_id` (String)
- **Purpose**: Stores user authentication information including hashed passwords, salts, and user metadata

#### AgentTable (Agent configurations and metadata)
- **Partition Key**: `user_id` (String)
- **Sort Key**: `id` (String)
- **Purpose**: Stores agent configurations and metadata with user isolation support

#### ChatRecordTable (Chat session records)
- **Partition Key**: `user_id` (String)
- **Sort Key**: `id` (String)
- **Purpose**: Stores chat conversation records with user isolation support

#### ChatResponseTable (Individual chat messages and responses)
- **Partition Key**: `id` (String)
- **Sort Key**: `resp_no` (Number)
- **Purpose**: Stores agent responses for each chat conversation

#### ChatSessionTable (Chat session management and memory storage)
- **Partition Key**: `PK` (String)
- **Sort Key**: `SK` (String)
- **Purpose**: Stores chat session data and memory information for agent conversations, enabling persistent context across chat interactions

**MCP and Advanced Features:**

#### HttpMCPTable (MCP server configurations)
- **Partition Key**: `user_id` (String)
- **Sort Key**: `id` (String)
- **Purpose**: Stores MCP server configurations with user isolation support

#### AgentScheduleTable (Scheduled agent tasks)
- **Partition Key**: `id` (String)
- **Purpose**: Stores scheduled agent task configurations

**Additional Tables** (used by orchestration and configuration features):

#### OrcheTable (Orchestration workflows)
- **Partition Key**: `user_id` (String)
- **Sort Key**: `id` (String)
- **Purpose**: Stores orchestration workflow definitions with user isolation

#### ConfTable (System configurations)
- **Partition Key**: `key` (String)
- **Purpose**: Stores system-wide configuration settings

> **Note**: All tables use pay-per-request billing mode and are configured with appropriate retention policies for production use.

### 4. User Authentication Features

The deployed application includes:

- **User Registration**: New users can create accounts with username/email and password
- **User Login**: JWT token-based authentication system
- **Data Isolation**: Each user's data (chat records, agents) is completely isolated
- **Session Management**: Secure token-based session handling
- **Password Security**: PBKDF2 hashing with individual salts for each user

### 5. Deployment Verification

After deployment is complete, you can verify the deployment by:

1. Checking the AWS CloudFormation console for stack status
2. Accessing the application using the ALB DNS name provided in the CloudFormation outputs
3. Monitoring the ECS services in the AWS ECS console
4. Testing user registration and login functionality
5. Verifying data isolation by creating multiple user accounts
6. **Testing Azure AD SSO** (if configured):
   - Click "Sign in with Microsoft" button on the login page
   - Verify redirect to Azure AD login page
   - Complete authentication with Azure AD credentials
   - Verify successful login and user profile synchronization
   - Check that user information is correctly stored in DynamoDB
   - Test logout and re-login functionality
