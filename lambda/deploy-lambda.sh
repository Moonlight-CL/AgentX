#!/bin/bash

# Deploy Agent Schedule Executor Lambda function
# Usage: ./deploy-lambda.sh <aws-region> [api-endpoint] [service-api-key]
# Example: ./deploy-lambda.sh us-west-2 https://agentx-eks.100.notnot.top/api/agent/async_chat my-api-key

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status()  { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Parameters ---
if [ -z "$1" ]; then
  print_error "AWS region is required"
  echo "Usage: $0 <aws-region> [api-endpoint] [service-api-key]"
  echo ""
  echo "  aws-region       : AWS region (e.g. us-west-2)"
  echo "  api-endpoint     : Backend async_chat URL (default: https://agentx-eks.100.notnot.top/api/agent/async_chat)"
  echo "  service-api-key  : X-API-Key for backend auth (reads from SECRET_API_KEY env var if not provided)"
  exit 1
fi

AWS_REGION=$1
API_ENDPOINT=${2:-"https://agentx-eks.100.notnot.top/api/agent/async_chat"}
SERVICE_API_KEY=${3:-${SERVICE_API_KEY:-""}}

FUNCTION_NAME="agentx-schedule-executor"
ROLE_NAME="agentx-schedule-executor-role"
SCHEDULER_ROLE_NAME="agentx-eventbridge-scheduler-role"
LAMBDA_DIR="$(cd "$(dirname "$0")/agent-schedule-executor" && pwd)"

print_status "Region: ${AWS_REGION}"
print_status "API endpoint: ${API_ENDPOINT}"
print_status "Lambda source: ${LAMBDA_DIR}"

# --- Get AWS Account ID ---
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_status "AWS Account: ${AWS_ACCOUNT_ID}"

LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${FUNCTION_NAME}"
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
SCHEDULER_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${SCHEDULER_ROLE_NAME}"

# ============================================================
# Step 1: Build Lambda code
# ============================================================
print_status "Building Lambda function..."
cd "${LAMBDA_DIR}"
npm install --silent
npm run build
print_success "Build complete"

# ============================================================
# Step 2: Package Lambda zip
# ============================================================
print_status "Packaging Lambda deployment..."
DEPLOY_DIR=$(mktemp -d)
cp -r dist/* "${DEPLOY_DIR}/"
cd "${DEPLOY_DIR}"
zip -r /tmp/agentx-lambda.zip . > /dev/null
cd - > /dev/null
rm -rf "${DEPLOY_DIR}"
print_success "Package created: /tmp/agentx-lambda.zip"

# ============================================================
# Step 3: Create Lambda execution role (if not exists)
# ============================================================
if aws iam get-role --role-name "${ROLE_NAME}" > /dev/null 2>&1; then
  print_status "Lambda execution role already exists: ${ROLE_NAME}"
else
  print_status "Creating Lambda execution role: ${ROLE_NAME}"
  aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' > /dev/null

  aws iam attach-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

  print_success "Lambda execution role created"
  print_status "Waiting for IAM role propagation..."
  sleep 10
fi

# ============================================================
# Step 4: Create or update Lambda function
# ============================================================
if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}" > /dev/null 2>&1; then
  print_status "Updating existing Lambda function..."
  aws lambda update-function-code \
    --function-name "${FUNCTION_NAME}" \
    --zip-file fileb:///tmp/agentx-lambda.zip \
    --region "${AWS_REGION}" > /dev/null

  # Wait for update to complete
  aws lambda wait function-updated --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}"

  aws lambda update-function-configuration \
    --function-name "${FUNCTION_NAME}" \
    --environment "Variables={API_ENDPOINT=${API_ENDPOINT},SERVICE_API_KEY=${SERVICE_API_KEY}}" \
    --timeout 30 \
    --region "${AWS_REGION}" > /dev/null

  print_success "Lambda function updated"
else
  print_status "Creating Lambda function: ${FUNCTION_NAME}"
  aws lambda create-function \
    --function-name "${FUNCTION_NAME}" \
    --runtime "nodejs20.x" \
    --handler "index.handler" \
    --role "${ROLE_ARN}" \
    --zip-file fileb:///tmp/agentx-lambda.zip \
    --timeout 30 \
    --memory-size 128 \
    --environment "Variables={API_ENDPOINT=${API_ENDPOINT},SERVICE_API_KEY=${SERVICE_API_KEY}}" \
    --architectures "arm64" \
    --region "${AWS_REGION}" > /dev/null

  aws lambda wait function-active --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}"
  print_success "Lambda function created"
fi

# ============================================================
# Step 5: Create EventBridge Scheduler execution role (if not exists)
# ============================================================
if aws iam get-role --role-name "${SCHEDULER_ROLE_NAME}" > /dev/null 2>&1; then
  print_status "EventBridge Scheduler role already exists: ${SCHEDULER_ROLE_NAME}"
else
  print_status "Creating EventBridge Scheduler role: ${SCHEDULER_ROLE_NAME}"
  aws iam create-role \
    --role-name "${SCHEDULER_ROLE_NAME}" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "scheduler.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' > /dev/null

  aws iam put-role-policy \
    --role-name "${SCHEDULER_ROLE_NAME}" \
    --policy-name "InvokeLambda" \
    --policy-document "{
      \"Version\": \"2012-10-17\",
      \"Statement\": [{
        \"Effect\": \"Allow\",
        \"Action\": \"lambda:InvokeFunction\",
        \"Resource\": \"${LAMBDA_ARN}\"
      }]
    }"

  print_success "EventBridge Scheduler role created"
fi

# ============================================================
# Step 6: Clean up
# ============================================================
rm -f /tmp/agentx-lambda.zip
print_success "Deployment complete!"

# ============================================================
# Output: values needed for K8s backend secrets
# ============================================================
echo ""
echo "============================================"
echo "  Lambda Deployment Summary"
echo "============================================"
echo ""
echo "Lambda Function ARN:"
echo "  ${LAMBDA_ARN}"
echo ""
echo "EventBridge Scheduler Role ARN:"
echo "  ${SCHEDULER_ROLE_ARN}"
echo ""
echo "Update your K8s backend secrets with:"
echo "  LAMBDA_FUNCTION_ARN=${LAMBDA_ARN}"
echo "  SCHEDULE_ROLE_ARN=${SCHEDULER_ROLE_ARN}"
echo ""
echo "To test the Lambda manually:"
echo "  aws lambda invoke --function-name ${FUNCTION_NAME} --region ${AWS_REGION} \\"
echo "    --payload '{\"user_id\":\"test\",\"agent_id\":\"test\",\"agent_owner_id\":\"test\",\"schedule_id\":\"test\"}' \\"
echo "    /tmp/lambda-output.json && cat /tmp/lambda-output.json"
echo ""
