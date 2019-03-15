#!/usr/bin/env python
"""
Script using Troposphere to generate a CFN Template which creates a new Lambda Function.
This Function sets a new commit in a newly created repository which didn't have a master branch
in order to allow CodePipeline (or else) to work on initialization
"""

from troposphere import (
    Template,
    Parameter,
    Output,
    GetAtt,
    Ref
)
from troposphere.awslambda import (
    Function,
    Code
)
from troposphere.ssm import (
    Parameter as SSMParam
)
from troposphere.iam import (
    Role, Policy
)

TEMPLATE = Template()
TEMPLATE.add_description(
    """Template to create the Lambda Function that initializes """
    """the codecommit repository with an initial branch to allow pipeline to work"""
)


FUNCTION_BUCKET = TEMPLATE.add_parameter(Parameter(
    "LambdaFunctionBucketName",
    Type="String",
    AllowedPattern="[\\x20-\\x7E]*"
))


FUNCTION_CODE_S3_KEY = TEMPLATE.add_parameter(Parameter(
    "LambdaFunctionS3Key",
    Type="String",
    AllowedPattern="[\\x20-\\x7E]*"
))


LAMBDA_ROLE = TEMPLATE.add_resource(Role(
    "LambdaRole",
    AssumeRolePolicyDocument={
        "Version" : "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "lambda.amazonaws.com"
                    ]
                },
                "Action": [
                    "sts:AssumeRole"
                ]
            }
        ]
    },
    Policies=[
        Policy(
            PolicyName="LambdaLayers-S3Access",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        'Effect': 'Allow',
                        'Resource': [
                            '*'
                        ],
                        'Action': [
                            "codecommit:CreateBranch",
                            "codecommit:CreateCommit",
                            "codecommit:GetBranch",
                            "codecommit:GetCommit",
                            "codecommit:GitPull",
                            "codecommit:GitPush",
                            "codecommit:ListBranches",
                            "codecommit:PutFile",
                            "codecommit:UpdateComment",
                            "codecommit:UpdateDefaultBranch",
                        ]
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-BuildCwLogsAccess",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        'Effect': 'Allow',
                        'Resource': '*',
                        'Action': [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ]
                    }
                ]
            }
        ),
    ]
))

LAMBDA_FUNCTION = TEMPLATE.add_resource(Function(
    "CodeCommitInit",
    Code=Code(
        S3Bucket=Ref(FUNCTION_BUCKET),
        S3Key=Ref(FUNCTION_CODE_S3_KEY)
    ),
    Handler='codecommit_repo_initializer.lambda_handler',
    Role=GetAtt(LAMBDA_ROLE, 'Arn'),
    Runtime="python3.7",
    MemorySize="128",
    Timeout=5,
))


SSM_FUNCTION_ARN = TEMPLATE.add_resource(SSMParam(
    "SsmLambdaFunctionArn",
    Name='CodePipelineTools-CodeCommitInit-Arn',
    Value=GetAtt(LAMBDA_FUNCTION, 'Arn'),
    Type="String"
))

SSM_FUNCTION_NAME = TEMPLATE.add_resource(SSMParam(
    "SsmLambdaFunctionName",
    Name='CodePipelineTools-CodeCommitInit-Name',
    Value=Ref(LAMBDA_FUNCTION),
    Type="String"
))

TEMPLATE.add_output([
    Output(
        "LambdaFunctionArn",
        Value=GetAtt(LAMBDA_FUNCTION, 'Arn'),
        Description="ARN of the Lambda Function"
    ),
    Output(
        "LambbdaFunctionName",
        Value=Ref(LAMBDA_FUNCTION),
        Description="Name of the Lambda Function"
    )
])


if __name__ == '__main__':
    import argparse
    import sys
    PARSER = argparse.ArgumentParser("Generate a template for a new Lambda Function")
    PARSER.add_argument(
        "--yaml", required=False, action='store_true',
        help="Render in YAML"
    )
    PARSER.add_argument(
        "--create-stack", action='store_true',
        help="Creates a new stack with the generated template"
    )
    PARSER.add_argument(
        "--s3-bucket", required=False,
        help="Name of the s3 bucket that contains the Layer code"
    )
    PARSER.add_argument(
        "--s3-key", required=False,
        help="Name of the s3 key that contains the Layer code"
    )
    ARGS = PARSER.parse_args()
    if ARGS.create_stack and not (ARGS.s3_bucket and ARGS.s3_key):
        print("Create stack requires the S3 bucket and S3 key paramters")
        sys.exit(1)
    if ARGS.yaml:
        print(TEMPLATE.to_yaml())
    else:
        print(TEMPLATE.to_json())

    if ARGS.create_stack:
        import boto3
        CLIENT = boto3.client('cloudformation')
        try:
            CLIENT.create_stack(
                StackName="CodePipeline-Tools-GitInit-platform",
                TemplateBody=TEMPLATE.to_json(),
                Parameters=[
                    {
                        'ParameterKey': FUNCTION_BUCKET.title,
                        'ParameterValue': ARGS.s3_bucket
                    },
                    {
                        'ParameterKey': FUNCTION_CODE_S3_KEY.title,
                        'ParameterValue': ARGS.s3_key
                    }
                ],
                Capabilities=[
                    'CAPABILITY_NAMED_IAM'
                ],
                OnFailure='DELETE',
                Tags=[
                    {
                        'Key': '20-business:department',
                        'Value': 'PlatformEngineering'
                    }
                ]
            )
        except Exception as error:
            print(error)
