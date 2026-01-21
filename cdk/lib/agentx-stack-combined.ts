import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as path from 'path';
import * as agentcore from '@aws-cdk/aws-bedrock-agentcore-alpha';

export interface AgentXStackProps extends cdk.StackProps {
  /**
   * Optional existing VPC ID to use instead of creating a new VPC.
   * If not provided, a new VPC will be created.
   */
  vpcId?: string;

  /**
   * Whether to deploy the MySQL MCP server.
   * If not provided, defaults to true.
   */
  deployMysqlMcpServer?: boolean;

  /**
   * Whether to deploy the Redshift MCP server.
   * If not provided, defaults to true.
   */
  deployRedshiftMcpServer?: boolean;

  /**
   * Whether to deploy the DuckDB MCP server.
   * If not provided, defaults to true.
   */
  deployDuckDbMcpServer?: boolean;

  /**
   * Whether to deploy the OpenSearch MCP server.
   * If not provided, defaults to true.
   */
  deployOpenSearchMcpServer?: boolean;

  /**
   * Whether to deploy the AWS DB MCP server.
   * If not provided, defaults to true.
   */
  deployAwsDbMcpServer?: boolean;

  /**
   * CPU units for the AWS DB MCP server (256, 512, 1024, 2048, 4096).
   * If not provided, defaults to 1024 (1 vCPU).
   */
  awsDbMcpCpu?: number;

  /**
   * Memory in MiB for the AWS DB MCP server.
   * If not provided, defaults to 2048 (2GB).
   */
  awsDbMcpMemory?: number;

  /**
   * Whether to create DynamoDB tables used by agent and MCP services.
   * If not provided, defaults to true.
   */
  createDynamoDBTables?: boolean;

  /**
   * S3 bucket name for file storage.
   * If not provided, defaults to 'agentx-files-bucket'.
   */
  s3BucketName?: string;

  /**
   * S3 file prefix for file storage.
   * If not provided, defaults to 'agentx/files'.
   */
  s3FilePrefix?: string;

  /**
   * Azure AD Client ID for SSO authentication.
   * Optional - if not provided, Azure AD SSO will not be configured.
   */
  azureClientId?: string;

  /**
   * Azure AD Tenant ID for SSO authentication.
   * Optional - if not provided, Azure AD SSO will not be configured.
   */
  azureTenantId?: string;

  /**
   * Azure AD Client Secret for SSO authentication.
   * Optional - if not provided, Azure AD SSO will not be configured.
   */
  azureClientSecret?: string;

  /**
   * JWT Secret Key for token generation.
   * If not provided, a random key will be generated (not recommended for production).
   */
  jwtSecretKey?: string;

  /**
   * Service API Key for Lambda authentication.
   * Used by Lambda functions to authenticate with the backend API.
   */
  serviceApiKey?: string;
}

export class AgentXStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: AgentXStackProps) {
    super(scope, id, props);

    // Use existing VPC or create a new one
    let vpc: ec2.IVpc;
    
    if (props?.vpcId) {
      // Use existing VPC if ID is provided
      vpc = ec2.Vpc.fromLookup(this, 'ImportedVpc', {
        vpcId: props.vpcId
      });
      console.log(`Using existing VPC with ID: ${props.vpcId}`);
    } else {
      // Create a new VPC if no ID is provided
      vpc = new ec2.Vpc(this, 'AgentXVpc', {
        maxAzs: 2,
        natGateways: 1,
      });
      console.log('Created new VPC as no VPC ID was provided');
    }

    // Create an ECS cluster with Service Connect enabled
    const cluster = new ecs.Cluster(this, 'AgentXCluster', {
      vpc,
      containerInsights: true,
      defaultCloudMapNamespace: {
        name: 'agentx.ns',
      },
    });

    // Get S3 configuration parameters with defaults
    const s3BucketName = props?.s3BucketName || 'agentx-files-bucket';
    const s3FilePrefix = props?.s3FilePrefix || 'agentx/files';

    // Reference existing ECR repositories
    const beRepository = ecr.Repository.fromRepositoryName(this, 'BeRepository', 'agentx/be');
    const feRepository = ecr.Repository.fromRepositoryName(this, 'FeRepository', 'agentx/fe');
    const mcpMysqlRepository = ecr.Repository.fromRepositoryName(this, 'McpMysqlRepository', 'agentx/mcp-mysql');
    const mcpRedshiftRepository = ecr.Repository.fromRepositoryName(this, 'McpRedshiftRepository', 'agentx/mcp-redshift');
    const mcpDuckDbRepository = ecr.Repository.fromRepositoryName(this, 'McpDuckDbRepository', 'agentx/mcp-duckdb');
    const mcpOpenSearchRepository = ecr.Repository.fromRepositoryName(this, 'McpOpenSearchRepository', 'agentx/mcp-opensearch');
    const mcpAwsDbRepository = ecr.Repository.fromRepositoryName(this, 'McpAwsDbRepository', 'agentx/mcp-aws-db');
    const agentCoreRuntimeRepository = ecr.Repository.fromRepositoryName(this, 'AgentCoreRuntimeRepository', 'agentx/rt-agentcore');

    // Create a security group for the load balancer
    const lbSecurityGroup = new ec2.SecurityGroup(this, 'LbSecurityGroup', {
      vpc,
      description: 'Security group for the load balancer',
      allowAllOutbound: true,
    });
    lbSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow HTTP traffic');
    lbSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'Allow HTTPS traffic');

    // Create a security group for the services
    const serviceSecurityGroup = new ec2.SecurityGroup(this, 'ServiceSecurityGroup', {
      vpc,
      description: 'Security group for the ECS services',
      allowAllOutbound: true,
    });
    serviceSecurityGroup.addIngressRule(lbSecurityGroup, ec2.Port.tcp(8000), 'Allow traffic from LB to BE');
    serviceSecurityGroup.addIngressRule(lbSecurityGroup, ec2.Port.tcp(80), 'Allow traffic from LB to FE');
    serviceSecurityGroup.addIngressRule(lbSecurityGroup, ec2.Port.tcp(3000), 'Allow traffic from LB to MCP services');
    serviceSecurityGroup.addIngressRule(serviceSecurityGroup, ec2.Port.allTraffic(), 'Allow all traffic between services');

    // Create a load balancer
    const lb = new elbv2.ApplicationLoadBalancer(this, 'AgentXLB', {
      vpc,
      internetFacing: true,
      securityGroup: lbSecurityGroup,
      idleTimeout: cdk.Duration.minutes(20), // Set idle timeout to 20 minutes
    });

    // Create a task execution role
    const executionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Create task roles for each service with default SSM policy
    const beTaskRole = new iam.Role(this, 'BeTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    // beTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'));
    // beTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonDynamoDBFullAccess'));
    // beTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonBedrockFullAccess'));
    // For the convienience of testing, add administrator prolicy
    beTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess'));

    const feTaskRole = new iam.Role(this, 'FeTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    feTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'));

    const mcpMysqlTaskRole = new iam.Role(this, 'McpMysqlTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    mcpMysqlTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'));

    const mcpRedshiftTaskRole = new iam.Role(this, 'McpRedshiftTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    mcpRedshiftTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'));

    const mcpDuckDbTaskRole = new iam.Role(this, 'McpDuckDbTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    mcpDuckDbTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'));

    const mcpOpenSearchTaskRole = new iam.Role(this, 'McpOpenSearchTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    mcpOpenSearchTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'));

    const mcpAwsDbTaskRole = new iam.Role(this, 'McpAwsDbTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    mcpAwsDbTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess'));

    // Create log groups for each service
    const beLogGroup = new logs.LogGroup(this, 'BeLogGroup', {
      logGroupName: '/ecs/agentx-be',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_WEEK,
    });

    const feLogGroup = new logs.LogGroup(this, 'FeLogGroup', {
      logGroupName: '/ecs/agentx-fe',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_WEEK,
    });

    const mcpMysqlLogGroup = new logs.LogGroup(this, 'McpMysqlLogGroup', {
      logGroupName: '/ecs/agentx-mcp-mysql',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_WEEK,
    });

    const mcpRedshiftLogGroup = new logs.LogGroup(this, 'McpRedshiftLogGroup', {
      logGroupName: '/ecs/agentx-mcp-redshift',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_WEEK,
    });

    const mcpDuckDbLogGroup = new logs.LogGroup(this, 'McpDuckDbLogGroup', {
      logGroupName: '/ecs/agentx-mcp-duckdb',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_WEEK,
    });

    const mcpOpenSearchLogGroup = new logs.LogGroup(this, 'McpOpenSearchLogGroup', {
      logGroupName: '/ecs/agentx-mcp-opensearch',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_WEEK,
    });

    const mcpAwsDbLogGroup = new logs.LogGroup(this, 'McpAwsDbLogGroup', {
      logGroupName: '/ecs/agentx-mcp-aws-db',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.ONE_WEEK,
    });

    // Create task definitions for each service with their respective task roles
    const beTaskDefinition = new ecs.FargateTaskDefinition(this, 'BeTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole: beTaskRole,
    });

    const feTaskDefinition = new ecs.FargateTaskDefinition(this, 'FeTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole: feTaskRole,
    });

    const mcpMysqlTaskDefinition = new ecs.FargateTaskDefinition(this, 'McpMysqlTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole: mcpMysqlTaskRole,
    });

    const mcpRedshiftTaskDefinition = new ecs.FargateTaskDefinition(this, 'McpRedshiftTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole: mcpRedshiftTaskRole,
    });

    const mcpDuckDbTaskDefinition = new ecs.FargateTaskDefinition(this, 'McpDuckDbTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole: mcpDuckDbTaskRole,
    });

    const mcpOpenSearchTaskDefinition = new ecs.FargateTaskDefinition(this, 'McpOpenSearchTaskDefinition', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole: mcpOpenSearchTaskRole,
    });

    // Get container size parameters for AWS DB MCP server with defaults
    // First check context values, then props, then defaults
    const awsDbMcpCpu = this.node.tryGetContext('awsDbMcpCpu') || props?.awsDbMcpCpu || 1024; // Default to 1 vCPU (1024 units)
    const awsDbMcpMemory = this.node.tryGetContext('awsDbMcpMemory') || props?.awsDbMcpMemory || 2048; // Default to 2GB (2048 MiB)

    const mcpAwsDbTaskDefinition = new ecs.FargateTaskDefinition(this, 'McpAwsDbTaskDefinition', {
      memoryLimitMiB: awsDbMcpMemory,
      cpu: awsDbMcpCpu,
      executionRole,
      taskRole: mcpAwsDbTaskRole,
    });

    // Add container definitions for each service
    const beContainer = beTaskDefinition.addContainer('BeContainer', {
      image: ecs.ContainerImage.fromEcrRepository(beRepository),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'be',
        logGroup: beLogGroup,
      }),
      environment: {
        // Add environment variables as needed
        APP_ENV: 'production',
        AWS_REGION: this.region,
        BYPASS_TOOL_CONSENT: 'true',
        S3_BUCKET_NAME: s3BucketName,
        S3_FILE_PREFIX: s3FilePrefix,
        // Azure AD SSO configuration (optional)
        ...(props?.azureClientId && { AZURE_CLIENT_ID: props.azureClientId }),
        ...(props?.azureTenantId && { AZURE_TENANT_ID: props.azureTenantId }),
        ...(props?.azureClientSecret && { AZURE_CLIENT_SECRET: props.azureClientSecret }),
        // JWT configuration
        ...(props?.jwtSecretKey && { JWT_SECRET_KEY: props.jwtSecretKey }),
        // Service API Key for Lambda authentication
        ...(props?.serviceApiKey && { SERVICE_API_KEY: props.serviceApiKey }),
      },
      portMappings: [
        {
          name: 'be-svr',
          containerPort: 8000,
          hostPort: 8000,
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    const feContainer = feTaskDefinition.addContainer('FeContainer', {
      image: ecs.ContainerImage.fromEcrRepository(feRepository),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'fe',
        logGroup: feLogGroup,
      }),
      environment: {
        // Add environment variables as needed
        NODE_ENV: 'production',
        AWS_REGION: this.region,
        // Azure AD SSO configuration (optional)
        ...(props?.azureClientId && { VITE_AZURE_CLIENT_ID: props.azureClientId }),
        ...(props?.azureTenantId && { VITE_AZURE_TENANT_ID: props.azureTenantId }),
        ...(props?.azureTenantId && { VITE_AZURE_AUTHORITY: `https://login.microsoftonline.com/${props.azureTenantId}` }),
      },
      portMappings: [
        {
          name: 'fe-svr',
          containerPort: 80,
          hostPort: 80,
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    const mcpMysqlContainer = mcpMysqlTaskDefinition.addContainer('McpMysqlContainer', {
      image: ecs.ContainerImage.fromEcrRepository(mcpMysqlRepository),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'mcp-mysql',
        logGroup: mcpMysqlLogGroup,
      }),
      environment: {
        // Add environment variables as needed
        NODE_ENV: 'production',
        AWS_REGION: this.region,
      },
      portMappings: [
        {
          name: 'mcp-mysql-svr',
          containerPort: 3000,
          hostPort: 3000,
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    const mcpRedshiftContainer = mcpRedshiftTaskDefinition.addContainer('McpRedshiftContainer', {
      image: ecs.ContainerImage.fromEcrRepository(mcpRedshiftRepository),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'mcp-redshift',
        logGroup: mcpRedshiftLogGroup,
      }),
      environment: {
        // Add environment variables as needed
        PYTHON_ENV: 'production',
        AWS_REGION: this.region,
      },
      portMappings: [
        {
          name: 'mcp-redshift-svr',
          containerPort: 3000,
          hostPort: 3000,
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    const mcpDuckDbContainer = mcpDuckDbTaskDefinition.addContainer('McpDuckDbContainer', {
      image: ecs.ContainerImage.fromEcrRepository(mcpDuckDbRepository),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'mcp-duckdb',
        logGroup: mcpDuckDbLogGroup,
      }),
      environment: {
        // Add environment variables as needed
        PYTHON_ENV: 'production',
        AWS_REGION: this.region,
        PORT: '8000',
      },
      portMappings: [
        {
          name: 'mcp-duckdb-svr',
          containerPort: 8000,
          hostPort: 8000,
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    const mcpOpenSearchContainer = mcpOpenSearchTaskDefinition.addContainer('McpOpenSearchContainer', {
      image: ecs.ContainerImage.fromEcrRepository(mcpOpenSearchRepository),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'mcp-opensearch',
        logGroup: mcpOpenSearchLogGroup,
      }),
      environment: {
        // Add environment variables as needed
        NODE_ENV: 'production',
        AWS_REGION: this.region,
      },
      portMappings: [
        {
          name: 'mcp-opensearch-svr',
          containerPort: 3000,
          hostPort: 3000,
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    const mcpAwsDbContainer = mcpAwsDbTaskDefinition.addContainer('McpAwsDbContainer', {
      image: ecs.ContainerImage.fromEcrRepository(mcpAwsDbRepository),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'mcp-aws-db',
        logGroup: mcpAwsDbLogGroup,
      }),
      environment: {
        // Add environment variables as needed
        PYTHON_ENV: 'production',
        AWS_REGION: this.region,
      },
      portMappings: [
        {
          name: 'mcp-aws-db-svr',
          containerPort: 3000,
          hostPort: 3000,
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    // Determine whether to deploy MCP servers and create DynamoDB tables based on props
    const deployMysqlMcpServer = props?.deployMysqlMcpServer !== false; // Default to true if not specified
    const deployRedshiftMcpServer = props?.deployRedshiftMcpServer !== false; // Default to true if not specified
    const deployDuckDbMcpServer = props?.deployDuckDbMcpServer !== false; // Default to true if not specified
    const deployOpenSearchMcpServer = props?.deployOpenSearchMcpServer !== false; // Default to true if not specified
    const deployAwsDbMcpServer = props?.deployAwsDbMcpServer !== false; // Default to true if not specified
    const createDynamoDBTables = props?.createDynamoDBTables !== false; // Default to true if not specified
    
    // Conditionally create DynamoDB tables for agent and MCP services
    if (createDynamoDBTables) {
      // Create DynamoDB table for user management
      const userTable = new cdk.aws_dynamodb.Table(this, 'UserTable', {
        tableName: 'UserTable',
        partitionKey: { name: 'user_id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      // Create DynamoDB tables used by agent.py with new user isolation schema
      const agentTable = new cdk.aws_dynamodb.Table(this, 'AgentTable', {
        tableName: 'AgentTable',
        partitionKey: { name: 'user_id', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      const chatRecordTable = new cdk.aws_dynamodb.Table(this, 'ChatRecordTable', {
        tableName: 'ChatRecordTable',
        partitionKey: { name: 'user_id', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      const chatResponseTable = new cdk.aws_dynamodb.Table(this, 'ChatResponseTable', {
        tableName: 'ChatResponseTable',
        partitionKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'resp_no', type: cdk.aws_dynamodb.AttributeType.NUMBER },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      // Create DynamoDB table used by mcp.py with new user isolation schema
      const httpMcpTable = new cdk.aws_dynamodb.Table(this, 'HttpMCPTable', {
        tableName: 'HttpMCPTable',
        partitionKey: { name: 'user_id', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      // Create DynamoDB table for agent schedules with user isolation
      const scheduleTable = new cdk.aws_dynamodb.Table(this, 'AgentScheduleTable', {
        tableName: 'AgentScheduleTable',
        partitionKey: { name: 'user_id', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      // Create DynamoDB table for chat sessions
      const chatSessionTable = new cdk.aws_dynamodb.Table(this, 'ChatSessionTable', {
        tableName: 'ChatSessionTable',
        partitionKey: { name: 'PK', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'SK', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      // Create DynamoDB table for orchestration workflows
      const orchestrationTable = new cdk.aws_dynamodb.Table(this, 'OrcheTable', {
        tableName: 'OrcheTable',
        partitionKey: { name: 'user_id', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      // Create DynamoDB table for orchestration executions
      const orchestrationExecutionTable = new cdk.aws_dynamodb.Table(this, 'OrcheExecTable', {
        tableName: 'OrcheExecTable',
        partitionKey: { name: 'user_id', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      // Create DynamoDB table for system configurations
      const configTable = new cdk.aws_dynamodb.Table(this, 'ConfTable', {
        tableName: 'ConfTable',
        partitionKey: { name: 'key', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });
      
      console.log('DynamoDB tables for agent, user management, and MCP services will be created');
    } else {
      console.log('DynamoDB tables creation is disabled');
    }

    // Create target groups for each service
    const beTargetGroup = new elbv2.ApplicationTargetGroup(this, 'BeTargetGroup', {
      vpc,
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/',
        interval: cdk.Duration.seconds(60),
        timeout: cdk.Duration.seconds(5),
        healthyHttpCodes: '200',
      },
    });

    const feTargetGroup = new elbv2.ApplicationTargetGroup(this, 'FeTargetGroup', {
      vpc,
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targetType: elbv2.TargetType.IP,
      healthCheck: {
        path: '/',
        interval: cdk.Duration.seconds(60),
        timeout: cdk.Duration.seconds(5),
        healthyHttpCodes: '200',
      },
    });

    // Conditionally create target groups for MCP services
    let mcpMysqlTargetGroup: elbv2.ApplicationTargetGroup | undefined;
    if (deployMysqlMcpServer) {
      mcpMysqlTargetGroup = new elbv2.ApplicationTargetGroup(this, 'McpMysqlTargetGroup', {
        vpc,
        port: 3000,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targetType: elbv2.TargetType.IP,
        healthCheck: {
          path: '/health',
          interval: cdk.Duration.seconds(60),
          timeout: cdk.Duration.seconds(5),
          healthyHttpCodes: '200',
        },
      });
    }

    let mcpRedshiftTargetGroup: elbv2.ApplicationTargetGroup | undefined;
    if (deployRedshiftMcpServer) {
      mcpRedshiftTargetGroup = new elbv2.ApplicationTargetGroup(this, 'McpRedshiftTargetGroup', {
        vpc,
        port: 3000,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targetType: elbv2.TargetType.IP,
        healthCheck: {
          path: '/health',
          interval: cdk.Duration.seconds(60),
          timeout: cdk.Duration.seconds(5),
          healthyHttpCodes: '200',
        },
      });
    }

    let mcpDuckDbTargetGroup: elbv2.ApplicationTargetGroup | undefined;
    if (deployDuckDbMcpServer) {
      mcpDuckDbTargetGroup = new elbv2.ApplicationTargetGroup(this, 'McpDuckDbTargetGroup', {
        vpc,
        port: 8000,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targetType: elbv2.TargetType.IP,
        healthCheck: {
          path: '/mcp',
          interval: cdk.Duration.seconds(60),
          timeout: cdk.Duration.seconds(5),
          healthyHttpCodes: '307',
        },
      });
    }

    let mcpOpenSearchTargetGroup: elbv2.ApplicationTargetGroup | undefined;
    if (deployOpenSearchMcpServer) {
      mcpOpenSearchTargetGroup = new elbv2.ApplicationTargetGroup(this, 'McpOpenSearchTargetGroup', {
        vpc,
        port: 3000,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targetType: elbv2.TargetType.IP,
        healthCheck: {
          path: '/health',
          interval: cdk.Duration.seconds(60),
          timeout: cdk.Duration.seconds(5),
          healthyHttpCodes: '200',
        },
      });
    }

    let mcpAwsDbTargetGroup: elbv2.ApplicationTargetGroup | undefined;
    if (deployAwsDbMcpServer) {
      mcpAwsDbTargetGroup = new elbv2.ApplicationTargetGroup(this, 'McpAwsDbTargetGroup', {
        vpc,
        port: 3000,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targetType: elbv2.TargetType.IP,
        healthCheck: {
          path: '/health',
          interval: cdk.Duration.seconds(60),
          timeout: cdk.Duration.seconds(5),
          healthyHttpCodes: '200',
        },
      });
    }

    // Create a listener for HTTP with default action to forward to frontend
    const httpListener = lb.addListener('HttpListener', {
      port: 80,
      open: true,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultAction: elbv2.ListenerAction.forward([feTargetGroup]),
    });

    // Add rules to the HTTP listener

    // Add rule for backend API
    httpListener.addAction('BeAction', {
      conditions: [
        elbv2.ListenerCondition.pathPatterns(['/api/*']),
      ],
      priority: 10,
      action: elbv2.ListenerAction.forward([beTargetGroup]),
    });

    // Conditionally add listener rules for MCP services
    if (deployMysqlMcpServer && mcpMysqlTargetGroup) {
      httpListener.addAction('McpMysqlAction', {
        conditions: [
          elbv2.ListenerCondition.pathPatterns(['/mcp-server/mysql/*']),
        ],
        priority: 20,
        action: elbv2.ListenerAction.forward([mcpMysqlTargetGroup]),
      });
    }

    if (deployRedshiftMcpServer && mcpRedshiftTargetGroup) {
      httpListener.addAction('McpRedshiftAction', {
        conditions: [
          elbv2.ListenerCondition.pathPatterns(['/mcp-server/redshift/*']),
        ],
        priority: 30,
        action: elbv2.ListenerAction.forward([mcpRedshiftTargetGroup]),
      });
    }

    if (deployDuckDbMcpServer && mcpDuckDbTargetGroup) {
      httpListener.addAction('McpDuckDbAction', {
        conditions: [
          elbv2.ListenerCondition.pathPatterns(['/mcp-server/duckdb/*']),
        ],
        priority: 40,
        action: elbv2.ListenerAction.forward([mcpDuckDbTargetGroup]),
      });
    }

    if (deployOpenSearchMcpServer && mcpOpenSearchTargetGroup) {
      httpListener.addAction('McpOpenSearchAction', {
        conditions: [
          elbv2.ListenerCondition.pathPatterns(['/mcp-server/opensearch/*']),
        ],
        priority: 50,
        action: elbv2.ListenerAction.forward([mcpOpenSearchTargetGroup]),
      });
    }

    if (deployAwsDbMcpServer && mcpAwsDbTargetGroup) {
      httpListener.addAction('McpAwsDbAction', {
        conditions: [
          elbv2.ListenerCondition.pathPatterns(['/mcp-server/aws-db/*']),
        ],
        priority: 60,
        action: elbv2.ListenerAction.forward([mcpAwsDbTargetGroup]),
      });
    }

    // Create services for each task definition with Service Connect enabled
    const beService = new ecs.FargateService(this, 'BeService', {
      cluster,
      taskDefinition: beTaskDefinition,
      desiredCount: 2,
      securityGroups: [serviceSecurityGroup],
      assignPublicIp: false,
      serviceConnectConfiguration: {
        namespace: 'agentx.ns',
        services: [
          {
            portMappingName: 'be-svr',
            dnsName: 'be',
            port: 8000,
          },
        ],
      },
    });

    const feService = new ecs.FargateService(this, 'FeService', {
      cluster,
      taskDefinition: feTaskDefinition,
      desiredCount: 2,
      securityGroups: [serviceSecurityGroup],
      assignPublicIp: false,
      serviceConnectConfiguration: {
        namespace: 'agentx.ns',
        services: [
          {
            portMappingName: 'fe-svr',
            dnsName: 'fe',
            port: 80,
          },
        ],
      },
    });

    // Conditionally create MySQL MCP service with Service Connect
    let mcpMysqlService: ecs.FargateService | undefined;
    if (deployMysqlMcpServer) {
      mcpMysqlService = new ecs.FargateService(this, 'McpMysqlService', {
        cluster,
        taskDefinition: mcpMysqlTaskDefinition,
        desiredCount: 1,
        securityGroups: [serviceSecurityGroup],
        assignPublicIp: false,
        serviceConnectConfiguration: {
          namespace: 'agentx.ns',
          services: [
            {
              portMappingName: 'mcp-mysql-svr',
              dnsName: 'mcp-mysql',
              port: 3000,
            },
          ],
        },
      });
      console.log('MySQL MCP server will be deployed');
    } else {
      console.log('MySQL MCP server deployment is disabled');
    }

    // Conditionally create Redshift MCP service with Service Connect
    let mcpRedshiftService: ecs.FargateService | undefined;
    if (deployRedshiftMcpServer) {
      mcpRedshiftService = new ecs.FargateService(this, 'McpRedshiftService', {
        cluster,
        taskDefinition: mcpRedshiftTaskDefinition,
        desiredCount: 1,
        securityGroups: [serviceSecurityGroup],
        assignPublicIp: false,
        serviceConnectConfiguration: {
          namespace: 'agentx.ns',
          services: [
            {
              portMappingName: 'mcp-redshift-svr',
              dnsName: 'mcp-redshift',
              port: 3000,
            },
          ],
        },
      });
      console.log('Redshift MCP server will be deployed');
    } else {
      console.log('Redshift MCP server deployment is disabled');
    }

    // Conditionally create DuckDB MCP service with Service Connect
    let mcpDuckDbService: ecs.FargateService | undefined;
    if (deployDuckDbMcpServer) {
      mcpDuckDbService = new ecs.FargateService(this, 'McpDuckDbService', {
        cluster,
        taskDefinition: mcpDuckDbTaskDefinition,
        desiredCount: 1,
        securityGroups: [serviceSecurityGroup],
        assignPublicIp: false,
        serviceConnectConfiguration: {
          namespace: 'agentx.ns',
          services: [
            {
              portMappingName: 'mcp-duckdb-svr',
              dnsName: 'mcp-duckdb',
              port: 8000,
            },
          ],
        },
      });
      console.log('DuckDB MCP server will be deployed');
    } else {
      console.log('DuckDB MCP server deployment is disabled');
    }

    // Conditionally create OpenSearch MCP service with Service Connect
    let mcpOpenSearchService: ecs.FargateService | undefined;
    if (deployOpenSearchMcpServer) {
      mcpOpenSearchService = new ecs.FargateService(this, 'McpOpenSearchService', {
        cluster,
        taskDefinition: mcpOpenSearchTaskDefinition,
        desiredCount: 1,
        securityGroups: [serviceSecurityGroup],
        assignPublicIp: false,
        serviceConnectConfiguration: {
          namespace: 'agentx.ns',
          services: [
            {
              portMappingName: 'mcp-opensearch-svr',
              dnsName: 'mcp-opensearch',
              port: 3000,
            },
          ],
        },
      });
      console.log('OpenSearch MCP server will be deployed');
    } else {
      console.log('OpenSearch MCP server deployment is disabled');
    }

    // Conditionally create AWS DB MCP service with Service Connect
    let mcpAwsDbService: ecs.FargateService | undefined;
    if (deployAwsDbMcpServer) {
      mcpAwsDbService = new ecs.FargateService(this, 'McpAwsDbService', {
        cluster,
        taskDefinition: mcpAwsDbTaskDefinition,
        desiredCount: 1,
        securityGroups: [serviceSecurityGroup],
        assignPublicIp: false,
        serviceConnectConfiguration: {
          namespace: 'agentx.ns',
          services: [
            {
              portMappingName: 'mcp-aws-db-svr',
              dnsName: 'mcp-aws-db',
              port: 3000,
            },
          ],
        },
      });
      console.log('AWS DB MCP server will be deployed');
    } else {
      console.log('AWS DB MCP server deployment is disabled');
    }

    // Register services with target groups
    beTargetGroup.addTarget(beService);
    feTargetGroup.addTarget(feService);
    
    // Conditionally register MCP services with target groups
    if (deployMysqlMcpServer && mcpMysqlService && mcpMysqlTargetGroup) {
      mcpMysqlTargetGroup.addTarget(mcpMysqlService);
    }
    
    if (deployRedshiftMcpServer && mcpRedshiftService && mcpRedshiftTargetGroup) {
      mcpRedshiftTargetGroup.addTarget(mcpRedshiftService);
    }
    
    if (deployDuckDbMcpServer && mcpDuckDbService && mcpDuckDbTargetGroup) {
      mcpDuckDbTargetGroup.addTarget(mcpDuckDbService);
    }
    
    if (deployOpenSearchMcpServer && mcpOpenSearchService && mcpOpenSearchTargetGroup) {
      mcpOpenSearchTargetGroup.addTarget(mcpOpenSearchService);
    }
    
    if (deployAwsDbMcpServer && mcpAwsDbService && mcpAwsDbTargetGroup) {
      mcpAwsDbTargetGroup.addTarget(mcpAwsDbService);
    }

    // Output the load balancer DNS name
    new cdk.CfnOutput(this, 'LoadBalancerDNS', {
      value: lb.loadBalancerDnsName,
      description: 'The DNS name of the load balancer',
      exportName: 'LoadBalancerDNS',
    });

    // Deploy AgentCore Runtime
    const agentCoreRuntimeArn = this.deployAgentCoreRuntime(agentCoreRuntimeRepository, s3BucketName, s3FilePrefix);

    // Add AgentCore Runtime ARN to BE container environment variables
    beContainer.addEnvironment('AGENTCORE_RUNTIME_ARN', agentCoreRuntimeArn);

    // Deploy Agent Schedule functionality
    const { lambdaFunctionArn, schedulerRoleArn } = this.deployAgentScheduleResources(lb.loadBalancerDnsName, beContainer);

    // Output the Lambda function ARN and role ARN
    new cdk.CfnOutput(this, 'AgentScheduleExecutorFunctionArn', {
      value: lambdaFunctionArn,
      description: 'The ARN of the Lambda function that executes scheduled agent tasks',
      exportName: 'AgentScheduleExecutorFunctionArn',
    });

    new cdk.CfnOutput(this, 'EventBridgeSchedulerRoleArn', {
      value: schedulerRoleArn,
      description: 'The ARN of the IAM role for EventBridge Scheduler',
      exportName: 'EventBridgeSchedulerRoleArn',
    });
  }

  /**
   * Deploy Agent Schedule resources including Lambda function and EventBridge Scheduler role
   * @param loadBalancerDnsName The DNS name of the load balancer
   * @param beContainer The backend container to add environment variables to
   * @returns The ARNs of the created resources
   */
  private deployAgentScheduleResources(loadBalancerDnsName: string, beContainer: ecs.ContainerDefinition): { lambdaFunctionArn: string, schedulerRoleArn: string } {
    console.log('Deploying Agent Schedule functionality');

    // Create IAM role for the Lambda function
    const lambdaRole = new iam.Role(this, 'AgentScheduleExecutorRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // Determine API endpoint
    let apiEndpoint = process.env.API_ENDPOINT || `http://${loadBalancerDnsName}/api/agent/async_chat`;
    console.log(`Using API endpoint for Lambda: ${apiEndpoint}`);

    // Get SERVICE_API_KEY from stack props
    const serviceApiKey = this.node.tryGetContext('serviceApiKey') || process.env.SERVICE_API_KEY || '';
    if (!serviceApiKey) {
      console.warn('WARNING: SERVICE_API_KEY not provided. Lambda function will not be able to authenticate with the backend API.');
    } else {
      console.log('SERVICE_API_KEY configured for Lambda function');
    }

    // Create Lambda function for executing scheduled agent tasks
    const schedulerLambda = new lambda.Function(this, 'AgentScheduleExecutorFunction', {
      runtime: lambda.Runtime.NODEJS_20_X,
      handler: 'dist/index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, 'lambda/agent-schedule-executor')),
      role: lambdaRole,
      timeout: cdk.Duration.seconds(30),
      environment: {
        API_ENDPOINT: apiEndpoint,
        SERVICE_API_KEY: serviceApiKey,
      },
    });

    // Create IAM role for EventBridge Scheduler
    const schedulerRole = new iam.Role(this, 'EventBridgeSchedulerRole', {
      // roleName: 'EventBridgeSchedulerExecutionRole',
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
    });

    // Allow EventBridge Scheduler to invoke the Lambda function
    schedulerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['lambda:InvokeFunction'],
        resources: [schedulerLambda.functionArn],
      })
    );

    // Add environment variables to the backend service for Lambda function ARN and scheduler role ARN
    beContainer.addEnvironment('LAMBDA_FUNCTION_ARN', schedulerLambda.functionArn);
    beContainer.addEnvironment('SCHEDULE_ROLE_ARN', schedulerRole.roleArn);

    return {
      lambdaFunctionArn: schedulerLambda.functionArn,
      schedulerRoleArn: schedulerRole.roleArn
    };
  }

  /**
   * Deploy AgentCore Runtime for AgentX
   * @param repository The ECR repository containing the AgentCore Runtime image
   * @param s3BucketName S3 bucket name for file storage
   * @param s3FilePrefix S3 file prefix for file storage
   * @returns The ARN of the created AgentCore Runtime
   */
  private deployAgentCoreRuntime(repository: ecr.IRepository, s3BucketName: string, s3FilePrefix: string): string {
    console.log('Deploying AgentCore Runtime');

    // Create IAM execution role for AgentCore Runtime
    const agentCoreExecutionRole = new iam.Role(this, 'AgentCoreRuntimeExecutionRole', {
      assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
      managedPolicies: [
        // For testing purposes, using AdministratorAccess as requested
        iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess'),
      ],
    });

    // Create AgentRuntimeArtifact from ECR repository
    const agentRuntimeArtifact = agentcore.AgentRuntimeArtifact.fromEcrRepository(
      repository,
      'latest'
    );

    // Create AgentCore Runtime
    const runtime = new agentcore.Runtime(this, 'AgentXAgentCoreRuntime', {
      runtimeName: 'agentx_runtime',
      agentRuntimeArtifact: agentRuntimeArtifact,
      executionRole: agentCoreExecutionRole,
      environmentVariables: {
        S3_BUCKET_NAME: s3BucketName,
        S3_FILE_PREFIX: s3FilePrefix,
        AWS_REGION: this.region,
      },
      networkConfiguration: agentcore.RuntimeNetworkConfiguration.usingPublicNetwork(),
    });

    // Output the AgentCore Runtime ARN
    new cdk.CfnOutput(this, 'AgentCoreRuntimeArn', {
      value: runtime.agentRuntimeArn,
      description: 'The ARN of the AgentCore Runtime',
      exportName: 'AgentCoreRuntimeArn',
    });

    console.log('AgentCore Runtime will be deployed');
    return runtime.agentRuntimeArn;
  }
}
