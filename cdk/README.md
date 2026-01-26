# AgentX AWS CDK Deployment

This project contains AWS CDK code to deploy the AgentX application to AWS ECS.

## Prerequisites

- AWS CLI installed and configured
- Node.js 18.x or later
- AWS CDK v2 installed (`npm install -g aws-cdk`)
- Docker installed
- AWS account with appropriate permissions

## Project Structure

- `bin/cdk.ts` - Standard CDK entry point
- `bin/cdk-combined.ts` - Combined CDK entry point with all stacks
- `lib/agentx-stack-combined.ts` - Main stack definition with all AWS resources
- `lib/agent-schedule-stack.ts` - Stack for agent scheduling functionality
- `lib/lambda/` - Lambda function code

## Components

The deployment includes the following components:

1. **Backend (BE)** - FastAPI Python application
2. **Frontend (FE)** - React/TypeScript application
3. **Agent Schedule** - Lambda function for executing scheduled agent tasks
4. **AgentCore Runtime** - Bedrock AgentCore runtime for agent execution

## Deployment Process

### Step 1: Create ECR Repositories

Before building and pushing Docker images, create ECR repositories:

```bash
# Set your AWS region
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create ECR repositories
aws ecr create-repository --repository-name agentx/be --region $AWS_REGION
aws ecr create-repository --repository-name agentx/fe --region $AWS_REGION
aws ecr create-repository --repository-name agentx/rt-agentcore --region $AWS_REGION
```

### Step 2: Build and Push Docker Images

Build and push Docker images for each component:

```bash
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push backend image
cd ../be
docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/be:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/be:latest

# Build and push frontend image
cd ../fe
docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/fe:latest .
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/agentx/fe:latest
```

Alternatively, you can use the provided script:

```bash
# Make the script executable
chmod +x ../build-and-push.sh

# Run the script with your AWS region
../build-and-push.sh us-west-2
```

### Step 3: Deploy with CDK

After pushing the Docker images to ECR, deploy the infrastructure:

#### Using the Automated Script (Recommended)

```bash
# Make the script executable
chmod +x deploy.sh

# Run the deployment script with options
./deploy.sh --region us-west-2
```

Available options:
- `--region REGION`: AWS region to deploy to
- `--vpc-id VPC_ID`: Use existing VPC ID instead of creating a new one
- `--no-dynamodb-tables`: Disable creation of DynamoDB tables
- `--s3-bucket-name BUCKET`: S3 bucket name for file storage
- `--s3-file-prefix PREFIX`: S3 file prefix for file storage
- `--azure-client-id ID`: Azure AD Client ID for SSO (optional)
- `--azure-tenant-id ID`: Azure AD Tenant ID for SSO (optional)
- `--azure-client-secret SEC`: Azure AD Client Secret for SSO (optional)
- `--jwt-secret-key KEY`: JWT Secret Key for token generation
- `--service-api-key KEY`: Service API Key for Lambda authentication

#### Manual CDK Deployment

```bash
# Install dependencies
npm install

# Bootstrap CDK (if not already done)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-west-2
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION

# Deploy the stacks
cdk --app "npx ts-node --prefer-ts-exts bin/cdk-combined.ts" deploy AgentXStack
```

### Step 4: Configuration

After deployment, you'll need to configure the following:

1. **Environment Variables**: Update environment variables in the CDK stack for each service as needed.
2. **SSL Certificate**: For production, create and attach an SSL certificate to the HTTPS listener.

## Useful CDK Commands

* `npm run build` - Compile TypeScript to JavaScript
* `npm run watch` - Watch for changes and compile
* `cdk deploy` - Deploy this stack to your default AWS account/region
* `cdk diff` - Compare deployed stack with current state
* `cdk synth` - Emit the synthesized CloudFormation template

## VPC Configuration

The stack supports two VPC deployment options:

### Option 1: Create a New VPC (Default)

If you don't specify a VPC ID, the stack will create a new VPC with:
- 2 Availability Zones
- 1 NAT Gateway
- Public and private subnets

This is suitable for testing or when you need a dedicated VPC for the application.

### Option 2: Use an Existing VPC

You can deploy the stack into an existing VPC by providing the VPC ID:

```bash
# Using deploy.sh script
./deploy.sh --region us-west-2 --vpc-id vpc-12345678

# OR using CDK context parameter
cdk --app "npx ts-node --prefer-ts-exts bin/cdk-combined.ts" deploy AgentXStack -c vpcId=vpc-12345678
```

Requirements for the existing VPC:
- Must have both public and private subnets
- Private subnets must have outbound internet connectivity (via NAT Gateway or similar)
- Subnets must be properly tagged for ECS and ALB resource placement

## Security Considerations

- The CDK stack creates security groups that allow traffic between services.
- For production, you should review and tighten security settings.
- Consider using AWS Secrets Manager for sensitive environment variables.

## Cost Optimization

- The stack uses Fargate for simplicity, but you could use EC2 instances for cost savings.
- Consider adjusting the desired count of services based on your traffic needs.
- NAT Gateways incur costs; consider using VPC endpoints for AWS services.

## Troubleshooting

If you encounter issues during deployment:

1. Check that AWS credentials are correctly configured
2. Verify that the CDK is bootstrapped in the target region
3. Ensure all Docker images are built and pushed to ECR
4. Check CloudFormation events for detailed error messages

For more detailed deployment instructions, see the [main deployment guide](../README-DEPLOYMENT.md).
