import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as logs from 'aws-cdk-lib/aws-logs';

export interface AgentXStackProps extends cdk.StackProps {
  /**
   * Optional existing VPC ID to use instead of creating a new VPC.
   * If not provided, a new VPC will be created.
   */
  vpcId?: string;

  /**
   * Whether to create DynamoDB tables used by agent services.
   * If not provided, defaults to true.
   */
  createDynamoDBTables?: boolean;
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

    // Reference existing ECR repositories
    const beRepository = ecr.Repository.fromRepositoryName(this, 'BeRepository', 'agentx/be');
    const feRepository = ecr.Repository.fromRepositoryName(this, 'FeRepository', 'agentx/fe');

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

    // Conditionally create DynamoDB tables for agent services
    if (createDynamoDBTables) {
      // Create DynamoDB tables used by agent.py
      const agentTable = new cdk.aws_dynamodb.Table(this, 'AgentTable', {
        tableName: 'AgentTable',
        partitionKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });

      const chatRecordTable = new cdk.aws_dynamodb.Table(this, 'ChatRecordTable', {
        tableName: 'ChatRecordTable',
        partitionKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
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

      // Create DynamoDB table used by mcp.py
      const httpMcpTable = new cdk.aws_dynamodb.Table(this, 'HttpMCPTable', {
        tableName: 'HttpMCPTable',
        partitionKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });

      console.log('DynamoDB tables for agent services will be created');
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
  }
}
