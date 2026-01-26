#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AgentXStack } from '../lib/agentx-stack-combined';

const app = new cdk.App();

const vpcId = app.node.tryGetContext('vpcId') || process.env.VPC_ID;
const createDynamoDBTables = app.node.tryGetContext('createDynamoDBTables') !== 'false' && process.env.CREATE_DYNAMODB_TABLES !== 'false';

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
  description: 'AgentX application stack with backend, frontend, and scheduling functionality',
  // Pass the parameters
  vpcId: vpcId,
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
console.log(`DynamoDB tables creation: ${createDynamoDBTables ? 'Enabled' : 'Disabled'}`);
console.log(`S3 bucket name: ${s3BucketName}`);
console.log(`S3 file prefix: ${s3FilePrefix}`);
console.log(`Azure AD SSO: ${azureClientId ? 'Enabled' : 'Disabled (username/password only)'}`);
console.log(`JWT Secret Key: ${jwtSecretKey ? 'Configured' : 'Not configured (will use default)'}`);
console.log(`Service API Key: ${serviceApiKey ? 'Configured' : 'Not configured (Lambda authentication will fail)'}`);
