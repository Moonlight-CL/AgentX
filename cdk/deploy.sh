#!/bin/bash

# Exit on error
set -e

# Function to display usage
usage() {
  echo "Usage: $0 [OPTIONS]"
  echo "Options:"
  echo "  --region REGION             AWS region to deploy to (default: from AWS config or us-west-2)"
  echo "  --vpc-id VPC_ID             Use existing VPC ID instead of creating a new one"
  echo "  --no-dynamodb-tables        Disable creation of DynamoDB tables for agent services"
  echo "  --s3-bucket-name BUCKET     S3 bucket name for file storage (default: agentx-files-bucket)"
  echo "  --s3-file-prefix PREFIX     S3 file prefix for file storage (default: agentx/files)"
  echo "  --azure-client-id ID        Azure AD Client ID for SSO (optional)"
  echo "  --azure-tenant-id ID        Azure AD Tenant ID for SSO (optional)"
  echo "  --azure-client-secret SEC   Azure AD Client Secret for SSO (optional)"
  echo "  --jwt-secret-key KEY        JWT Secret Key for token generation (optional, uses default if not provided)"
  echo "  --service-api-key KEY       Service API Key for Lambda authentication (optional, auto-generated if not provided)"
  echo "  --help                      Display this help message"
  exit 1
}

# Default values
AWS_REGION=$(aws configure get region || echo "us-west-2")
VPC_ID=""
CREATE_DYNAMODB_TABLES=true
S3_BUCKET_NAME="agentx-files-bucket"
S3_FILE_PREFIX="agentx/files"
AZURE_CLIENT_ID=""
AZURE_TENANT_ID=""
AZURE_CLIENT_SECRET=""
JWT_SECRET_KEY=""
SERVICE_API_KEY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --vpc-id)
      VPC_ID="$2"
      shift 2
      ;;
    --no-dynamodb-tables)
      CREATE_DYNAMODB_TABLES=false
      shift
      ;;
    --s3-bucket-name)
      S3_BUCKET_NAME="$2"
      shift 2
      ;;
    --s3-file-prefix)
      S3_FILE_PREFIX="$2"
      shift 2
      ;;
    --azure-client-id)
      AZURE_CLIENT_ID="$2"
      shift 2
      ;;
    --azure-tenant-id)
      AZURE_TENANT_ID="$2"
      shift 2
      ;;
    --azure-client-secret)
      AZURE_CLIENT_SECRET="$2"
      shift 2
      ;;
    --jwt-secret-key)
      JWT_SECRET_KEY="$2"
      shift 2
      ;;
    --service-api-key)
      SERVICE_API_KEY="$2"
      shift 2
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

echo "Using AWS region: ${AWS_REGION}"
if [ -n "$VPC_ID" ]; then
  echo "Using existing VPC: ${VPC_ID}"
fi
echo "DynamoDB tables creation: $([ "$CREATE_DYNAMODB_TABLES" = true ] && echo "Enabled" || echo "Disabled")"
echo "S3 bucket name: ${S3_BUCKET_NAME}"
echo "S3 file prefix: ${S3_FILE_PREFIX}"
echo "Agent Schedule functionality: Enabled"
if [ -n "$AZURE_CLIENT_ID" ]; then
  echo "Azure AD SSO: Enabled"
else
  echo "Azure AD SSO: Disabled (username/password only)"
fi
if [ -n "$JWT_SECRET_KEY" ]; then
  echo "JWT Secret Key: Custom key provided"
else
  echo "JWT Secret Key: Using default (not recommended for production)"
fi

# Generate SERVICE_API_KEY if not provided
if [ -z "$SERVICE_API_KEY" ]; then
  echo "SERVICE_API_KEY not provided, generating a new one..."
  # Generate a 64-character random API key using openssl
  SERVICE_API_KEY=$(openssl rand -base64 48 | tr -d "=+/" | cut -c1-64)
  echo "Generated SERVICE_API_KEY: ${SERVICE_API_KEY:0:20}... (truncated for security)"
  echo "IMPORTANT: Save this key securely. It will be needed for backend configuration."
  echo "Full key will be saved to .service-api-key file"
  echo "$SERVICE_API_KEY" > .service-api-key
  chmod 600 .service-api-key
else
  echo "SERVICE_API_KEY: Custom key provided"
fi

# Bootstrap CDK if not already done
echo "Checking if CDK is bootstrapped..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ $? -ne 0 ]; then
  echo "Error: Failed to get AWS account ID. Make sure you're logged in to AWS CLI."
  exit 1
fi

# Check if bootstrap is already done
aws cloudformation describe-stacks --stack-name CDKToolkit --region ${AWS_REGION} > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Bootstrapping CDK in account ${AWS_ACCOUNT_ID} region ${AWS_REGION}..."
  cdk bootstrap aws://${AWS_ACCOUNT_ID}/${AWS_REGION}
else
  echo "CDK is already bootstrapped in this account and region."
fi

# Build CDK parameters
CDK_PARAMS=""

# Add VPC ID if provided
if [ -n "$VPC_ID" ]; then
  CDK_PARAMS="$CDK_PARAMS -c vpcId=$VPC_ID"
fi

# Add S3 configuration parameters
CDK_PARAMS="$CDK_PARAMS -c s3BucketName=$S3_BUCKET_NAME"
CDK_PARAMS="$CDK_PARAMS -c s3FilePrefix=$S3_FILE_PREFIX"

if [ "$CREATE_DYNAMODB_TABLES" = false ]; then
  CDK_PARAMS="$CDK_PARAMS -c createDynamoDBTables=false"
  export CREATE_DYNAMODB_TABLES=false
fi

# Add Azure AD and JWT configuration parameters
if [ -n "$AZURE_CLIENT_ID" ]; then
  CDK_PARAMS="$CDK_PARAMS -c azureClientId=$AZURE_CLIENT_ID"
fi

if [ -n "$AZURE_TENANT_ID" ]; then
  CDK_PARAMS="$CDK_PARAMS -c azureTenantId=$AZURE_TENANT_ID"
fi

if [ -n "$AZURE_CLIENT_SECRET" ]; then
  CDK_PARAMS="$CDK_PARAMS -c azureClientSecret=$AZURE_CLIENT_SECRET"
fi

if [ -n "$JWT_SECRET_KEY" ]; then
  CDK_PARAMS="$CDK_PARAMS -c jwtSecretKey=$JWT_SECRET_KEY"
fi

# Add SERVICE_API_KEY as CDK context parameter
if [ -n "$SERVICE_API_KEY" ]; then
  CDK_PARAMS="$CDK_PARAMS -c serviceApiKey=$SERVICE_API_KEY"
fi

# Export SERVICE_API_KEY for CDK
export SERVICE_API_KEY=$SERVICE_API_KEY

# Export S3 configuration for CDK
export S3_BUCKET_NAME=$S3_BUCKET_NAME
export S3_FILE_PREFIX=$S3_FILE_PREFIX


# Set AWS region
export AWS_DEFAULT_REGION=$AWS_REGION

# Build Lambda functions for Agent Schedule functionality
echo "Building Lambda functions for Agent Schedule functionality..."
(cd lib/lambda/agent-schedule-executor && npm install && npm run build)

# Deploy the stack using the combined CDK app
echo "Deploying AgentX stack with combined functionality..."
echo "CDK parameters: $CDK_PARAMS"
cdk --app "npx ts-node --prefer-ts-exts bin/cdk-combined.ts" deploy --require-approval never AgentXStack $CDK_PARAMS

echo "Deployment complete!"
echo "Check the AWS CloudFormation console for stack status and outputs."
