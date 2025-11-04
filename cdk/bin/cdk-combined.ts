#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AgentXStack } from '../lib/agentx-stack-combined';

const app = new cdk.App();

// Get parameters from context or environment variables
// Users can provide parameters using:
// 1. CDK context: cdk deploy -c vpcId=vpc-12345 -c deployMysqlMcpServer=false
// 2. Environment variables: VPC_ID=vpc-12345 DEPLOY_MYSQL_MCP=false cdk deploy
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
