import * as cdk from 'aws-cdk-lib';
import { Rule, Schedule } from 'aws-cdk-lib/aws-events';
import { LambdaFunction as LambdaFunctionTgt } from 'aws-cdk-lib/aws-events-targets';
import { ManagedPolicy, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Code, Function, Runtime } from 'aws-cdk-lib/aws-lambda';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const lambdaRole = new Role(this, 'apartment_check_lambda_role', {
      roleName: 'apartment_check_lambda_role',
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSNSFullAccess')
      ],
    });

    const lambdaFunction = new Function(this, 'apartment_check_lambda', {
      functionName: 'apartment_check_lambda',
      runtime: Runtime.PYTHON_3_12,
      code: Code.fromAsset('../code/'),
      handler: 'apartment_check.lambda_function.lambda_handler',
      role: lambdaRole,
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      logRetention: RetentionDays.ONE_WEEK,
    });

    new Rule(this, 'apartment_check_rule', {
      ruleName: 'apartment_check_rule',
      schedule: Schedule.rate(cdk.Duration.minutes(5)),
      targets: [
        new LambdaFunctionTgt(lambdaFunction, {
          maxEventAge: cdk.Duration.minutes(3),
          retryAttempts: 1,
        })
      ]
    });
  }
}
