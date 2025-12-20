import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as path from 'path';

export interface AgentScheduleStackProps extends cdk.StackProps {
  /**
   * Optional reference to the AgentX stack to get the load balancer DNS name.
   */
  agentXStack?: cdk.Stack;
}

export class AgentScheduleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: AgentScheduleStackProps) {
    super(scope, id, props);

    // Create DynamoDB table for agent schedules
    const scheduleTable = new dynamodb.Table(this, 'AgentScheduleTable', {
      tableName: 'AgentScheduleTable',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Create IAM role for the Lambda function
    const lambdaRole = new iam.Role(this, 'AgentScheduleExecutorRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // Add permissions to invoke the API
    // lambdaRole.addToPolicy(
    //   new iam.PolicyStatement({
    //     actions: ['execute-api:Invoke'],
    //     resources: ['*'], // Scope this down in production
    //   })
    // );

    // Determine API endpoint
    let apiEndpoint = process.env.API_ENDPOINT || 'https://api.example.com/api/agent/async_chat';
    
    // If AgentX stack is provided, try to get the load balancer DNS name
    if (props?.agentXStack) {
      try {
        // Get the load balancer DNS name from the AgentX stack outputs
        const lbDnsName = cdk.Fn.importValue('LoadBalancerDNS');
        if (lbDnsName) {
          apiEndpoint = `http://${lbDnsName}/api/agent/async_chat`;
          console.log(`Using AgentX load balancer for API endpoint: ${apiEndpoint}`);
        }
      } catch (error) {
        console.warn('Could not import LoadBalancerDNS from AgentX stack, using default API endpoint');
      }
    } else {
      console.log(`Using default or environment-provided API endpoint: ${apiEndpoint}`);
    }

    // Get SERVICE_API_KEY from environment variable
    const serviceApiKey = process.env.SERVICE_API_KEY || '';
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
        // AWS_REGION: this.region,
      },
    });

    // Create IAM role for EventBridge Scheduler
    const schedulerRole = new iam.Role(this, 'EventBridgeSchedulerRole', {
      roleName: 'EventBridgeSchedulerExecutionRole',
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
    });

    // Allow EventBridge Scheduler to invoke the Lambda function
    schedulerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['lambda:InvokeFunction'],
        resources: [schedulerLambda.functionArn],
      })
    );

    // Output the Lambda function ARN and role ARN
    new cdk.CfnOutput(this, 'AgentScheduleExecutorFunctionArn', {
      value: schedulerLambda.functionArn,
      description: 'The ARN of the Lambda function that executes scheduled agent tasks',
      exportName: 'AgentScheduleExecutorFunctionArn',
    });

    new cdk.CfnOutput(this, 'EventBridgeSchedulerRoleArn', {
      value: schedulerRole.roleArn,
      description: 'The ARN of the IAM role for EventBridge Scheduler',
      exportName: 'EventBridgeSchedulerRoleArn',
    });
  }
}
