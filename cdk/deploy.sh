#!/bin/bash

# Exit on error
set -e

# Function to display usage
usage() {
  echo "Usage: $0 [OPTIONS]"
  echo "Options:"
  echo "  --region REGION             AWS region to deploy to (default: from AWS config or us-west-2)"
  echo "  --vpc-id VPC_ID             Use existing VPC ID instead of creating a new one"
  echo "  --no-mysql-mcp              Disable MySQL MCP server deployment"
  echo "  --no-redshift-mcp           Disable Redshift MCP server deployment"
  echo "  --no-dynamodb-tables        Disable creation of DynamoDB tables for agent and MCP services"
  echo "  --help                      Display this help message"
  exit 1
}

# Default values
AWS_REGION=$(aws configure get region || echo "us-west-2")
VPC_ID=""
DEPLOY_MYSQL_MCP=true
DEPLOY_REDSHIFT_MCP=true
CREATE_DYNAMODB_TABLES=true

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
    --no-mysql-mcp)
      DEPLOY_MYSQL_MCP=false
      shift
      ;;
    --no-redshift-mcp)
      DEPLOY_REDSHIFT_MCP=false
      shift
      ;;
    --no-dynamodb-tables)
      CREATE_DYNAMODB_TABLES=false
      shift
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
echo "MySQL MCP server deployment: $([ "$DEPLOY_MYSQL_MCP" = true ] && echo "Enabled" || echo "Disabled")"
echo "Redshift MCP server deployment: $([ "$DEPLOY_REDSHIFT_MCP" = true ] && echo "Enabled" || echo "Disabled")"
echo "DynamoDB tables creation: $([ "$CREATE_DYNAMODB_TABLES" = true ] && echo "Enabled" || echo "Disabled")"
echo "Agent Schedule functionality: Enabled"

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

# Add deployment parameters
if [ "$DEPLOY_MYSQL_MCP" = false ]; then
  CDK_PARAMS="$CDK_PARAMS -c deployMysqlMcpServer=false"
  export DEPLOY_MYSQL_MCP=false
fi

if [ "$DEPLOY_REDSHIFT_MCP" = false ]; then
  CDK_PARAMS="$CDK_PARAMS -c deployRedshiftMcpServer=false"
  export DEPLOY_REDSHIFT_MCP=false
fi

if [ "$CREATE_DYNAMODB_TABLES" = false ]; then
  CDK_PARAMS="$CDK_PARAMS -c createDynamoDBTables=false"
  export CREATE_DYNAMODB_TABLES=false
fi


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
