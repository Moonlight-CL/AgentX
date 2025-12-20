#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AgentXStack } from '../lib/agentx-stack-combined';

const app = new cdk.App();

const vpcId = app.node.tryGetContext('vpcId') || process.env.VPC_ID;
const deployMysqlMcpServer = app.node.tryGetContext('deployMysqlMcpServer') !== 'false' && process.env.DEPLOY_MYSQL_MCP !== 'false';
const deployRedshiftMcpServer = app.node.tryGetContext('deployRedshiftMcpServer') !== 'false' && process.env.DEPLOY_REDSHIFT_MCP !== 'false';
const deployDuckDbMcpServer = app.node.tryGetContext('deployDuckDbMcpServer') !== 'false' && process.env.DEPLOY_DUCKDB_MCP !== 'false';
const deployOpenSearchMcpServer = app.node.tryGetContext('deployOpenSearchMcpServer') !== 'false' && process.env.DEPLOY_OPENSEARCH_MCP !== 'false';
const deployAwsDbMcpServer = app.node.tryGetContext('deployAwsDbMcpServer') !== 'false' && process.env.DEPLOY_AWS_DB_MCP !== 'false';
const createDynamoDBTables = app.node.tryGetContext('createDynamoDBTables') !== 'false' && process.env.CREATE_DYNAMODB_TABLES !== 'false';

// AWS DB MCP container size parameters
const awsDbMcpCpu = parseInt(app.node.tryGetContext('awsDbMcpCpu') || process.env.AWS_DB_MCP_CPU || '1024');
const awsDbMcpMemory = parseInt(app.node.tryGetContext('awsDbMcpMemory') || process.env.AWS_DB_MCP_MEMORY || '2048');

// S3 configuration parameters
const s3BucketName = app.node.tryGetContext('s3BucketName') || process.env.S3_BUCKET_NAME || 'agentx-files-bucket';
const s3FilePrefix = app.node.tryGetContext('s3FilePrefix') || process.env.S3_FILE_PREFIX || 'agentx/files';

// Azure AD SSO Configuration parameters
const azureClientId = app.node.tryGetContext('azureClientId') || process.env.AZURE_CLIENT_ID;
const azureTenantId = app.node.tryGetContext('azureTenantId') || process.env.AZURE_TENANT_ID;
const azureClientSecret = app.node.tryGetContext('azureClientSecret') || process.env.AZURE_CLIENT_SECRET;

// JWT Secret Key
const jwtSecretKey = app.node.tryGetContext('jwtSecretKey') || process.env.JWT_SECRET_KEY;

// Service API Key for Lambda authentication
const serviceApiKey = app.node.tryGetContext('serviceApiKey') || process.env.SERVICE_API_KEY;

// Create the combined AgentX stack
new AgentXStack(app, 'AgentXStack', {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2' 
  },
  description: 'AgentX application stack with backend, frontend, MCP services, and scheduling functionality',
  // Pass the parameters
  vpcId: vpcId,
  deployMysqlMcpServer: deployMysqlMcpServer,
  deployRedshiftMcpServer: deployRedshiftMcpServer,
  deployDuckDbMcpServer: deployDuckDbMcpServer,
  deployOpenSearchMcpServer: deployOpenSearchMcpServer,
  deployAwsDbMcpServer: deployAwsDbMcpServer,
  awsDbMcpCpu: awsDbMcpCpu,
  awsDbMcpMemory: awsDbMcpMemory,
  createDynamoDBTables: createDynamoDBTables,
  s3BucketName: s3BucketName,
  s3FilePrefix: s3FilePrefix,
  azureClientId: azureClientId,
  azureTenantId: azureTenantId,
  azureClientSecret: azureClientSecret,
  jwtSecretKey: jwtSecretKey,
  serviceApiKey: serviceApiKey,
});

// Log configuration
console.log(vpcId 
  ? `Using existing VPC with ID: ${vpcId}` 
  : 'No VPC ID provided. A new VPC will be created.');
console.log(`MySQL MCP server deployment: ${deployMysqlMcpServer ? 'Enabled' : 'Disabled'}`);
console.log(`Redshift MCP server deployment: ${deployRedshiftMcpServer ? 'Enabled' : 'Disabled'}`);
console.log(`DuckDB MCP server deployment: ${deployDuckDbMcpServer ? 'Enabled' : 'Disabled'}`);
console.log(`OpenSearch MCP server deployment: ${deployOpenSearchMcpServer ? 'Enabled' : 'Disabled'}`);
console.log(`AWS DB MCP server deployment: ${deployAwsDbMcpServer ? `Enabled (CPU: ${awsDbMcpCpu}, Memory: ${awsDbMcpMemory}MiB)` : 'Disabled'}`);
console.log(`DynamoDB tables creation: ${createDynamoDBTables ? 'Enabled' : 'Disabled'}`);
console.log(`S3 bucket name: ${s3BucketName}`);
console.log(`S3 file prefix: ${s3FilePrefix}`);
console.log(`Azure AD SSO: ${azureClientId ? 'Enabled' : 'Disabled (username/password only)'}`);
console.log(`JWT Secret Key: ${jwtSecretKey ? 'Configured' : 'Not configured (will use default)'}`);
console.log(`Service API Key: ${serviceApiKey ? 'Configured' : 'Not configured (Lambda authentication will fail)'}`);
