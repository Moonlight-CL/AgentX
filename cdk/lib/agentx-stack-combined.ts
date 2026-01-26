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
    // For the convenience of testing, add administrator policy
    beTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess'));

    const feTaskRole = new iam.Role(this, 'FeTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    feTaskRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'));

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

    // Determine whether to create DynamoDB tables based on props
    const createDynamoDBTables = props?.createDynamoDBTables !== false; // Default to true if not specified

    // Conditionally create DynamoDB tables for agent and services
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

      // Create DynamoDB table for REST API registry with user isolation
      const restApiRegistryTable = new cdk.aws_dynamodb.Table(this, 'RestAPIRegistryTable', {
        tableName: 'RestAPIRegistryTable',
        partitionKey: { name: 'user_id', type: cdk.aws_dynamodb.AttributeType.STRING },
        sortKey: { name: 'api_id', type: cdk.aws_dynamodb.AttributeType.STRING },
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

      console.log('DynamoDB tables for agent, user management, and services will be created');
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

    // Register services with target groups
    beTargetGroup.addTarget(beService);
    feTargetGroup.addTarget(feService);

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
