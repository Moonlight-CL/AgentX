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
const createDynamoDBTables = app.node.tryGetContext('createDynamoDBTables') !== 'false' && process.env.CREATE_DYNAMODB_TABLES !== 'false';

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
  createDynamoDBTables: createDynamoDBTables,
});

// Log configuration
console.log(vpcId 
  ? `Using existing VPC with ID: ${vpcId}` 
  : 'No VPC ID provided. A new VPC will be created.');
console.log(`MySQL MCP server deployment: ${deployMysqlMcpServer ? 'Enabled' : 'Disabled'}`);
console.log(`Redshift MCP server deployment: ${deployRedshiftMcpServer ? 'Enabled' : 'Disabled'}`);
console.log(`DuckDB MCP server deployment: ${deployDuckDbMcpServer ? 'Enabled' : 'Disabled'}`);
console.log(`OpenSearch MCP server deployment: ${deployOpenSearchMcpServer ? 'Enabled' : 'Disabled'}`);
console.log(`DynamoDB tables creation: ${createDynamoDBTables ? 'Enabled' : 'Disabled'}`);
