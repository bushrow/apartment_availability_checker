import * as cdk from 'aws-cdk-lib';
import { Rule, Schedule } from 'aws-cdk-lib/aws-events';
import { LambdaFunction as LambdaFunctionTgt } from 'aws-cdk-lib/aws-events-targets';
import { ManagedPolicy, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { Code, Function, Runtime } from 'aws-cdk-lib/aws-lambda';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { Topic } from 'aws-cdk-lib/aws-sns';
import { EmailSubscription } from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new Bucket(this, 'apartment_check_tracking_bucket', {
      bucketName: 'apartment_check_tracking_bucket',
    });

    const notificationTopic = new Topic(this, 'apartment_check_notification_topic', {
      topicName: 'apartment_check_notification_topic',
    });
    notificationTopic.addSubscription(new EmailSubscription('charlie.bushrow@gmail.com'));

    const lambdaRole = new Role(this, 'apartment_check_lambda_role', {
      roleName: 'apartment_check_lambda_role',
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonSNSFullAccess'),
        ManagedPolicy.fromAwsManagedPolicyName('AmazonS3FullAccess'),
      ],
    });

    const lambdaFunction = new Function(this, 'apartment_check_lambda', {
      functionName: 'apartment_check_lambda',
      runtime: Runtime.PYTHON_3_12,
      code: Code.fromAsset('../code/'),
      environment: {
        SNS_TOPIC_ARN: notificationTopic.topicArn,
        APT_MIN_BEDS: '2',
        APT_MIN_BATHS: '1.5',
        APT_MIN_SQ_FT: '0',
        APT_TGT_DATE: '2024-08-10',
      },
      handler: 'apartment_check.lambda_function.lambda_handler',
      role: lambdaRole,
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      logRetention: RetentionDays.ONE_WEEK,
    });

    new Rule(this, 'apartment_check_rule', {
      ruleName: 'apartment_check_rule',
      schedule: Schedule.rate(cdk.Duration.hours(6)),
      targets: [
        new LambdaFunctionTgt(lambdaFunction, {
          maxEventAge: cdk.Duration.minutes(3),
          retryAttempts: 1,
        })
      ]
    });
  }
}
