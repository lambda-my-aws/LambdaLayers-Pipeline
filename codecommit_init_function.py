from troposphere import (
    Template,
    Parameter,
    Output,
    Ref,
    Join,
    GetAtt
)
from troposphere.awslambda import (
    Function,
    Code,
    Content
)
from troposphere.ssm import (
    Parameter as SSMParam
)
from troposphere.iam import (
    Role, Policy
)

TEMPLATE = Template()
TEMPLATE.add_description("""Template to create the Lambda Function that initializes """
                         """the codecommit repository with an initial branch to allow pipeline to work"""
)

platform_init_bucket = TEMPLATE.add_parameter(Parameter(
    "PlatformInitialSourceBucket",
    Type="String",
    AllowedPattern="[\\x20-\\x7E]*"
))


codecommit_init_code_s3_key = TEMPLATE.add_parameter(Parameter(
    "CodeCommitCodeS3Key",
    Type="String",
    AllowedPattern="[\\x20-\\x7E]*"
))


lambda_role = TEMPLATE.add_resource(Role(
    "LambdaRole",
    AssumeRolePolicyDocument={
        "Version" : "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [ "lambda.amazonaws.com"
                             ]
                },
                "Action": [ "sts:AssumeRole" ]
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

lambda_function = TEMPLATE.add_resource(Function(
    "CodeCommitInit",
    Code=Code(
        S3Bucket=Ref(platform_init_bucket),
        S3Key=Ref(codecommit_init_code_s3_key)
    ),
    Handler='codecommit_repo_initializer.lambda_handler',
    Role=GetAtt(lambda_role, 'Arn'),
    Runtime="python3.7",
    MemorySize="128",
    Timeout=5,
))


ssm_function_arn = TEMPLATE.add_resource(SSMParam(
    "SsmLambdaFunctionArn",
    Name='CodePipelineTools-CodeCommitInit-Arn',
    Value=GetAtt(lambda_function, 'Arn'),
    Type="String"
))

ssm_function_name = TEMPLATE.add_resource(SSMParam(
    "SsmLambdaFunctionName",
    Name='CodePipelineTools-CodeCommitInit-Name',
    Value=Ref(lambda_function),
    Type="String"
))

TEMPLATE.add_output([
    Output(
        "LambdaFunctionArn",
        Value=GetAtt(lambda_function, 'Arn'),
        Description="ARN of the Lambda Function"
    ),
    Output(
        "LambbdaFunctionName",
        Value=Ref(lambda_function),
        Description="Name of the Lambda Function"
    )
])


if __name__ == '__main__':
    import argparse
    import sys
    PARSER = argparse.ArgumentParser("Generate a template for a new Lambda Function")
    PARSER.add_argument(
        "--yaml", required=False, action='store_true', help="Render in YAML"
    )
    PARSER.add_argument(
        "--create-stack", action='store_true', help="Creates a new stack with the generated template"
    )
    PARSER.add_argument(
        "--s3-bucket", required=False,
        help="Name of the s3 bucket that contains the Layer code"
    )
    PARSER.add_argument(
        "--s3-key", required=False, help="Name of the s3 key that contains the Layer code"
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
        client = boto3.client('cloudformation')
        try:
            client.create_stack(
                StackName="CodePipeline-Tools-GitInit-platform",
                TemplateBody=TEMPLATE.to_json(),
                Parameters=[
                    {
                        'ParameterKey': platform_init_bucket.title,
                        'ParameterValue': ARGS.s3_bucket
                    },
                    {
                        'ParameterKey': codecommit_init_code_s3_key.title,
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
        except Exception as e:
            print(e)

