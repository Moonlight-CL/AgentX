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
aws ecr describe-repositories --repository-names agentx/fe --region $AWS_REGION || aws ecr create-repository --repository-name agentx/fe --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/mcp-mysql --region $AWS_REGION || aws ecr create-repository --repository-name agentx/mcp-mysql --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/mcp-redshift --region $AWS_REGION || aws ecr create-repository --repository-name agentx/mcp-redshift --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/mcp-duckdb --region $AWS_REGION || aws ecr create-repository --repository-name agentx/mcp-duckdb --region $AWS_REGION
aws ecr describe-repositories --repository-names agentx/mcp-opensearch --region $AWS_REGION || aws ecr create-repository --repository-name agentx/mcp-opensearch --region $AWS_REGION

# Build and push backend
cd be
docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/be:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/be:latest

# Build and push frontend
cd ../fe
docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/fe:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/fe:latest

# Build and push MySQL MCP server
cd ../mcp/mysql
docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/mcp-mysql:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/mcp-mysql:latest

# Build and push Redshift MCP server
cd ../mcp/redshift
docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/mcp-redshift:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/mcp-redshift:latest
cd ../..
```

#### Step 3: Deploy with CDK

After pushing the Docker images to ECR, deploy the infrastructure using AWS CDK:

##### Option A: Using the Automated Script (Recommended)

```bash
# Make the script executable
chmod +x cdk/deploy.sh

# Navigate to the CDK directory
cd cdk

# Basic deployment
./deploy.sh --region us-west-2

# Deployment with custom S3 configuration
./deploy.sh --region us-west-2 --s3-bucket-name my-agentx-files --s3-file-prefix uploads/agentx

# Deployment with selective MCP servers and custom S3
./deploy.sh --region us-west-2 \
  --no-mysql-mcp \
  --no-redshift-mcp \
  --s3-bucket-name production-files \
  --s3-file-prefix agentx/prod/files

# Deployment with existing VPC and custom configuration
./deploy.sh --region us-west-2 \
  --vpc-id vpc-12345678 \
  --aws-db-mcp-cpu 2048 \
  --aws-db-mcp-memory 4096 \
  --s3-bucket-name enterprise-storage \
  --s3-file-prefix agentx/enterprise
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

## ⚙️ Configuration

### Environment Variables

Before deployment, you should update the environment variables in the CDK stack (`cdk/lib/agentx-stack-combined.ts`):

#### Backend Environment Variables

```typescript
const beContainer = beTaskDefinition.addContainer('BeContainer', {
  // ...
  environment: {
    APP_ENV: 'production',
    AWS_REGION: this.region,
    // Add other environment variables as needed
  },
});
```

#### Frontend Environment Variables

```typescript
const feContainer = feTaskDefinition.addContainer('FeContainer', {
  // ...
  environment: {
    NODE_ENV: 'production',
    API_BASE_URL: 'https://your-alb-dns-name/api',
    // Add other environment variables as needed
  },
});
```

#### MCP Server Environment Variables

```typescript
const mcpMysqlContainer = mcpMysqlTaskDefinition.addContainer('McpMysqlContainer', {
  // ...
  environment: {
    NODE_ENV: 'production',
    AWS_REGION: this.region,
    MYSQL_HOST: 'your-mysql-host',
    MYSQL_PORT: '3306',
    MYSQL_USER: 'your-mysql-user',
    MYSQL_PASSWORD: 'your-mysql-password',
    MYSQL_DATABASE: 'your-mysql-database',
  },
});

const mcpRedshiftContainer = mcpRedshiftTaskDefinition.addContainer('McpRedshiftContainer', {
  // ...
  environment: {
    PYTHON_ENV: 'production',
    AWS_REGION: this.region,
    RS_HOST: 'your-redshift-host',
    RS_PORT: '5439',
    RS_USER: 'your-redshift-user',
    RS_PASSWORD: 'your-redshift-password',
    RS_DATABASE: 'your-redshift-database',
    RS_SCHEMA: 'public',
  },
});

const mcpDuckDbContainer = mcpDuckDbTaskDefinition.addContainer('McpDuckDbContainer', {
  // ...
  environment: {
    PYTHON_ENV: 'production',
    AWS_REGION: this.region,
    PORT: '8000',
  },
});

const mcpOpenSearchContainer = mcpOpenSearchTaskDefinition.addContainer('McpOpenSearchContainer', {
  // ...
  environment: {
    NODE_ENV: 'production',
    AWS_REGION: this.region,
    OPENSEARCH_HOST: 'your-opensearch-host',
    OPENSEARCH_PORT: '9200',
    OPENSEARCH_USER: 'your-opensearch-user',
    OPENSEARCH_PASSWORD: 'your-opensearch-password',
  },
});
```

### Security Considerations

For production deployments, consider these security enhancements:

1. **Use AWS Secrets Manager** for sensitive environment variables:
   ```typescript
   const secret = secretsmanager.Secret.fromSecretNameV2(this, 'DbSecret', 'my-db-secret');
   container.addEnvironment('DB_PASSWORD', secret.secretValueFromJson('password').toString());
   ```

2. **Implement proper IAM roles and policies**:
   ```typescript
   const taskRole = new iam.Role(this, 'TaskRole', {
     assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
   });
   taskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonDynamoDBFullAccess'));
   ```

3. **Enable HTTPS** with an SSL certificate:
   ```typescript
   const certificate = acm.Certificate.fromCertificateArn(this, 'Certificate', 'arn:aws:acm:region:account:certificate/certificate-id');
   const httpsListener = lb.addListener('HttpsListener', {
     port: 443,
     certificates: [certificate],
     sslPolicy: elbv2.SslPolicy.RECOMMENDED,
   });
   ```

## 📊 Monitoring and Logging

### CloudWatch Logs

All services are configured to send logs to CloudWatch Logs:

```typescript
const logGroup = new logs.LogGroup(this, 'LogGroup', {
  logGroupName: '/ecs/agentx-service',
  removalPolicy: cdk.RemovalPolicy.DESTROY,
  retention: logs.RetentionDays.ONE_WEEK,
});

container.addLogging(ecs.LogDrivers.awsLogs({
  streamPrefix: 'service',
  logGroup: logGroup,
}));
```

### CloudWatch Alarms

Add CloudWatch Alarms for monitoring:

```typescript
new cloudwatch.Alarm(this, 'HighCpuAlarm', {
  metric: service.metricCpuUtilization(),
  threshold: 90,
  evaluationPeriods: 3,
  datapointsToAlarm: 2,
});
```

### X-Ray Tracing

Enable X-Ray for distributed tracing:

```typescript
const taskDefinition = new ecs.FargateTaskDefinition(this, 'TaskDef');
taskDefinition.addContainer('XRayDaemon', {
  image: ecs.ContainerImage.fromRegistry('amazon/aws-xray-daemon'),
  essential: true,
  portMappings: [{ containerPort: 2000, protocol: ecs.Protocol.UDP }],
});
```

## 💰 Cost Optimization

### Use EC2 Instead of Fargate

For cost savings, consider using EC2 launch type instead of Fargate:

```typescript
const service = new ecs.Ec2Service(this, 'Service', {
  cluster,
  taskDefinition,
  desiredCount: 2,
});
```

### Auto Scaling

Implement auto scaling to adjust capacity based on demand:

```typescript
const scaling = service.autoScaleTaskCount({
  minCapacity: 2,
  maxCapacity: 10,
});

scaling.scaleOnCpuUtilization('CpuScaling', {
  targetUtilizationPercent: 70,
});
```

### VPC Endpoints

Use VPC endpoints to reduce NAT Gateway costs:

```typescript
new ec2.InterfaceVpcEndpoint(this, 'DynamoDBEndpoint', {
  vpc,
  service: ec2.InterfaceVpcEndpointAwsService.DYNAMODB,
});
```

## 🔄 Continuous Deployment

### GitHub Actions

Create a GitHub Actions workflow for continuous deployment:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-west-2
      - name: Build and push Docker images
        run: ./build-and-push.sh us-west-2
      - name: Deploy with CDK
        run: |
          cd cdk
          npm install
          npm run cdk deploy -- --all --require-approval never
```

### AWS CodePipeline

Alternatively, set up AWS CodePipeline for continuous deployment:

```typescript
const pipeline = new codepipeline.Pipeline(this, 'Pipeline', {
  pipelineName: 'AgentXPipeline',
});

const sourceOutput = new codepipeline.Artifact();
const sourceAction = new codepipeline_actions.CodeStarConnectionsSourceAction({
  actionName: 'GitHub',
  owner: 'your-github-username',
  repo: 'agentx',
  branch: 'main',
  output: sourceOutput,
  connectionArn: 'arn:aws:codestar-connections:region:account:connection/connection-id',
});

pipeline.addStage({
  stageName: 'Source',
  actions: [sourceAction],
});

// Add build and deploy stages
```

## 🔍 Troubleshooting

### Common Issues

1. **Container fails to start**:
   - Check CloudWatch Logs for error messages
   - Verify environment variables are correctly set
   - Ensure IAM permissions are sufficient

2. **Load balancer health checks failing**:
   - Verify the health check path is correct
   - Check that the container is listening on the expected port
   - Ensure security groups allow traffic between the load balancer and containers

3. **CDK deployment errors**:
   - Check that AWS credentials are correctly configured
   - Verify that the CDK is bootstrapped in the target region
   - Check for syntax errors in CDK code

### Useful Commands

```bash
# View service logs
aws logs get-log-events --log-group-name /ecs/agentx-be --log-stream-name stream-name

# Check service status
aws ecs describe-services --cluster agentx-cluster --services agentx-be-service

# View task details
aws ecs describe-tasks --cluster agentx-cluster --tasks task-id

# SSH into EC2 instance (if using EC2 launch type)
aws ssm start-session --target instance-id
