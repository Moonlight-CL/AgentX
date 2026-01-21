#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS region is provided
if [ -z "$1" ]; then
  print_error "AWS region is required"
  echo "Usage: $0 <aws-region> [aws-account-id]"
  echo "Example: $0 us-east-1 123456789012"
  exit 1
fi

AWS_REGION=$1

# Get AWS account ID if not provided
if [ -z "$2" ]; then
  print_status "Getting AWS account ID..."
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  if [ $? -ne 0 ]; then
    print_error "Failed to get AWS account ID. Please provide it as the second argument."
    exit 1
  fi
  print_success "AWS Account ID: ${AWS_ACCOUNT_ID}"
else
  AWS_ACCOUNT_ID=$2
  print_status "Using provided AWS Account ID: ${AWS_ACCOUNT_ID}"
fi

# ECR registry URL
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
print_status "ECR Registry: ${ECR_REGISTRY}"

# Function to create ECR repository if it doesn't exist
create_repository() {
  local repo_name=$1
  print_status "Checking/creating ECR repository: ${repo_name}"
  aws ecr describe-repositories --repository-names ${repo_name} --region ${AWS_REGION} > /dev/null 2>&1 || \
  aws ecr create-repository --repository-name ${repo_name} --region ${AWS_REGION}
}

# Function to build and push Docker image
build_and_push() {
  local service_name=$1
  local image_name=$2
  local build_path=$3
  local repo_name=$4
  
  print_status "Building and pushing ${service_name} image..."
  
  # Check if Dockerfile exists
  if [ ! -f "${build_path}/Dockerfile" ]; then
    print_warning "Dockerfile not found in ${build_path}, skipping ${service_name}"
    return 0
  fi
  
  create_repository "${repo_name}"
  
  cd "${build_path}"
  docker build -t "${image_name}" .
  docker tag "${image_name}:latest" "${ECR_REGISTRY}/${repo_name}:latest"
  docker push "${ECR_REGISTRY}/${repo_name}:latest"
  cd - > /dev/null
  
  print_success "${service_name} image built and pushed successfully"
}

# Login to ECR
print_status "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
print_success "Successfully logged in to ECR"

# Build and push all images
print_status "Starting build and push process for all services..."

# Core services
build_and_push "Backend" "agentx-be" "be" "agentx/be"
build_and_push "Frontend" "agentx-fe" "fe" "agentx/fe"

# AgentCore Runtime
print_status "Building AgentCore Runtime image..."
# Check if Dockerfile.agentcore exists
if [ -f "be/Dockerfile.agentcore" ]; then
  create_repository "agentx/rt-agentcore"

  cd "be"
  # Build ARM64 image for AgentCore Runtime
  print_status "Building ARM64 image for AgentCore Runtime (this may take a while)..."
  docker buildx create --use --name agentcore-builder 2>/dev/null || docker buildx use agentcore-builder
  docker buildx build \
    --platform linux/arm64 \
    -f ./Dockerfile.agentcore \
    -t "agentx-rt-agentcore:latest" \
    -t "${ECR_REGISTRY}/agentx/rt-agentcore:latest" \
    --push \
    .
  cd - > /dev/null

  print_success "AgentCore Runtime image built and pushed successfully"
else
  print_warning "Dockerfile.agentcore not found in be/, skipping AgentCore Runtime"
fi

# MCP services
print_status "Building MCP services..."
build_and_push "MCP AWS-DB" "agentx-mcp-aws-db" "mcp/aws-db" "agentx/mcp-aws-db"
build_and_push "MCP DuckDB" "agentx-mcp-duckdb" "mcp/duckdb" "agentx/mcp-duckdb"
build_and_push "MCP MySQL" "agentx-mcp-mysql" "mcp/mysql" "agentx/mcp-mysql"
build_and_push "MCP OpenSearch" "agentx-mcp-opensearch" "mcp/opensearch" "agentx/mcp-opensearch"
build_and_push "MCP Redshift" "agentx-mcp-redshift" "mcp/redshift" "agentx/mcp-redshift"

print_success "All images have been built and pushed to ECR successfully!"
echo ""
print_status "Next steps:"
echo "1. cd cdk"
echo "2. npm install"
echo "3. cdk bootstrap (if not already done)"
echo "4. cdk deploy"
echo ""
print_status "Available ECR repositories:"
echo "- ${ECR_REGISTRY}/agentx/be:latest"
echo "- ${ECR_REGISTRY}/agentx/fe:latest"
echo "- ${ECR_REGISTRY}/agentx/rt-agentcore:latest"
echo "- ${ECR_REGISTRY}/agentx/mcp-aws-db:latest"
echo "- ${ECR_REGISTRY}/agentx/mcp-duckdb:latest"
echo "- ${ECR_REGISTRY}/agentx/mcp-mysql:latest"
echo "- ${ECR_REGISTRY}/agentx/mcp-opensearch:latest"
echo "- ${ECR_REGISTRY}/agentx/mcp-redshift:latest"
