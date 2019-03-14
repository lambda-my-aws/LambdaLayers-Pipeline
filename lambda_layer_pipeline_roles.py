from troposphere import (

    Template,
    Parameter,
    Output
)

from troposphere import (
    Ref,
    GetAtt,
    Sub
)

from troposphere.iam import (
    Role,
    Policy
)

from troposphere.ssm import (
    Parameter as SSMParam
)

TEMPLATE = Template()
TEMPLATE.add_description("Creates a role for CFN, CodeBuild and CodePipeline to create Lambda Layers")

# Parameters - need to have a value at CFN stack Creation


layers_build_artifacts_bucket_arn = TEMPLATE.add_parameter(Parameter(
    "DestArtifactsBucket",
    Description="Bucket in which store the built Lambda Layer",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="LambdaLayers-ArtifactsBucket"
))


cloudformation_role = TEMPLATE.add_resource(Role(
    "CloudFormationRole",
    RoleName='LambdaLayersBuild-CloudFormationRole',
    AssumeRolePolicyDocument={
        "Version" : "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "cloudformation.amazonaws.com"
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
                            Sub('arn:aws:s3:::${DestArtifactsBucket}/*')
                        ],
                        'Action': [
                            's3:PutObject',
                            's3:PutObjectVersion',
                            's3:GetObject',
                            's3:GetObjectVersion'
                        ]
                    }
                ]
            }
        ),
        Policy(
            PolicyName="GetAll",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            "lambda:List*",
                            "lambda:Get*"
                        ],
                        "Effect": "Allow",
                        "Resource": "*"
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-WriteAccess",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            'lambda:DeleteLayerVersion',
                            'lambda:TagResource',
                            'lambda:UntagResource',
                            'lambda:Publish*'
                        ],
                        "Effect": "Allow",
                        "Resource": "*"
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-PermissionsAccess",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            'lambda:AddLayerVersionPermission',
                            'lambda:AddPermission',
                            'lambda:EnableReplication',
                            'lambda:RemoveLayerVersionPermission',
                            'lambda:RemovePermission'
                        ],
                        "Effect": "Allow",
                        "Resource": "*"
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-CloudWatchAccess",
            PolicyDocument={
                "Version" : "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "events:PutRule",
                            "events:PutEvents",
                            "events:PutTargets",
                            "events:DeleteRule",
                            "events:RemoveTargets",
                            "events:DescribeRule"
                        ],
                        "Resource": "*"
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-SsmAccess",
            PolicyDocument={
                "Version" : "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ssm:PutParameter",
                            "ssm:DeleteParameter",
                            "ssm:DescribeParameters",
                            "ssm:GetParameters",
                            "ssm:GetParameter",
                            "ssm:DeleteParameters"
                        ],
                        "Resource": "*"
                    }
                ]
            }
        )
    ]
))


codebuild_role = TEMPLATE.add_resource(Role(
    "CodeBuildRole",
    RoleName='LambdaLayersBuild-CodeBuildRole',
    AssumeRolePolicyDocument={
        "Version" : "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [ "codebuild.amazonaws.com"
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
                            Sub('arn:aws:s3:::${DestArtifactsBucket}/*')
                        ],
                        'Action': [
                            's3:PutObject',
                            's3:PutObjectVersion',
                            's3:GetObject',
                            's3:GetObjectVersion'
                        ]
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-BuildLogsAccess",
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
        )
    ]
))

lambda_role = TEMPLATE.add_resource(Role(
    "LambdaRole",
    RoleName='LambdaLayersBuild-LambdaRole',
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
                            Sub('arn:aws:s3:::${DestArtifactsBucket}/*')
                        ],
                        'Action': [
                            's3:PutObject',
                            's3:PutObjectVersion',
                            's3:GetObject',
                            's3:GetObjectVersion'
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
        Policy(
            PolicyName="LambdaLayers-CodePipelineAccess",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        'Effect': 'Allow',
                        'Resource': '*',
                        'Action': [
                            "codepipeline:PutThirdPartyJobSuccessResult",
                            "codepipeline:PutThirdPartyJobFailureResult",
                            "codepipeline:PutApprovalResult",
                            "codepipeline:PutJobFailureResult",
                            "codepipeline:PutJobSuccessResult",
                            "codepipeline:PutActionRevision"
                        ]                    }
                ]
            }
        )
    ]
))


codepipeline_role = TEMPLATE.add_resource(Role(
    "CodePipelineRole",
    RoleName='LambdaLayersBuild-CodePipelineRole',
    AssumeRolePolicyDocument={
        "Version" : "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [ "codepipeline.amazonaws.com"
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
                            Sub('arn:aws:s3:::${DestArtifactsBucket}/*')
                        ],
                        'Action': [
                            's3:PutObject',
                            's3:PutObjectVersion',
                            's3:GetObject',
                            's3:GetObjectVersion'
                        ]
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-LambdaAccess",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        'Effect': 'Allow',
                        'Resource': [
                            '*'
                        ],
                        'Action': [
                            'lambda:Invoke',
                            'lambda:InvokeFunction',
                            'lambda:List*',
                            'lambda:Get*'
                        ]
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-PassRole",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            "iam:PassRole"
                        ],
                        "Resource": "*",
                        "Effect": "Allow",
                        "Condition": {
                            "StringEqualsIfExists": {
                                "iam:PassedToService": [
                                    "cloudformation.amazonaws.com",
                                ]
                            }
                        }
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-CodeCommitAccess",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement" : [
                    {
                        "Resource": "*",
                        "Effect": "Allow",
                        "Action": [
                            "codecommit:CancelUploadArchive",
                            "codecommit:GetBranch",
                            "codecommit:GetCommit",
                            "codecommit:GetUploadArchiveStatus",
                            "codecommit:UploadArchive"
                        ]
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-CloudFormationAccess",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Resource": "*",
                        "Action": [
                            "cloudformation:CreateStack",
                            "cloudformation:DeleteStack",
                            "cloudformation:DescribeStacks",
                            "cloudformation:UpdateStack",
                            "cloudformation:CreateChangeSet",
                            "cloudformation:DeleteChangeSet",
                            "cloudformation:DescribeChangeSet",
                            "cloudformation:ExecuteChangeSet",
                            "cloudformation:SetStackPolicy",
                            "cloudformation:ValidateTemplate"
                        ]
                    }
                ]
            }
        ),
        Policy(
            PolicyName="LambdaLayers-CodeBuildAccess",
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            "codebuild:BatchGetBuilds",
                            "codebuild:StartBuild"
                        ],
                        "Resource": "*",
                        "Effect": "Allow"
                    }
                ]
            }
        )
    ]
))


cloudformation_ssm = TEMPLATE.add_resource(SSMParam(
    "SsmCloudFormationRoleArn",
    Name='LambdaLayersPipeline-CloudFormationRoleArn',
    Value=GetAtt(cloudformation_role, 'Arn'),
    Type="String"
))

codebuild_ssm = TEMPLATE.add_resource(SSMParam(
    "SsmCodeBuildRoleArn",
    Name='LambdaLayersPipeline-CodeBuildRoleArn',
    Value=GetAtt(codebuild_role, 'Arn'),
    Type="String"
))

codepipeline_ssm = TEMPLATE.add_resource(SSMParam(
    "SsmCodePipelineRoleArn",
    Name='LambdaLayersPipeline-CodePipelineRoleArn',
    Value=GetAtt(codepipeline_role, 'Arn'),
    Type="String"
))

lambda_ssm = TEMPLATE.add_resource(SSMParam(
    "SsmLambdaRoleArn",
    Name='LambdaLayersPipeline-LambdaRoleArn',
    Value=GetAtt(lambda_role, 'Arn'),
    Type="String"
))

TEMPLATE.add_output([
    Output(
        "CloudFormationRoleArn",
        Value=GetAtt(cloudformation_role, 'Arn'),
        Description="ARN of the role for CFN to use for Lambda Layers pipelines"
    ),
    Output(
        "CodeBuildRoleArn",
        Value=GetAtt(codebuild_role, 'Arn'),
        Description="ARN of the role for CodeBuild to use for Lambda Layers pipelines"
    ),
    Output(
        "CloudFormationSsmParameterName",
        Value=Ref(cloudformation_ssm),
        Description="ARN of the role for CloudFormation to use for Lambda Layers pipelines"
    ),
    Output(
        "CodePipelineRoleArn",
        Value=GetAtt(codepipeline_role, 'Arn'),
        Description="ARN of the role for CodePipeline to use for Lambda Layers pipelines"
    ),
    Output(
        "LambdaRoleArn",
        Value=GetAtt(lambda_role, 'Arn'),
        Description="ARN of the role for Lambda to use for Lambda Layers pipelines to generate artifacts"
    ),
    Output(
        "CodeBuildSsmParameterName",
        Value=Ref(codebuild_ssm),
        Description="ARN of the role for CodeBuild to use for Lambda Layers pipelines"
    ),
    Output(
        "CodePipelineSsmParameterName",
        Value=Ref(codepipeline_ssm),
        Description="ARN of the role for CodePipeline to use for Lambda Layers pipelines"
    ),
    Output(
        "LambdaSsmParameterName",
        Value=Ref(lambda_ssm),
        Description="ARN of the role for Lambda to use for Lambda Layers pipelines to generate artifacts"
    )

])

if __name__ == '__main__':
    import argparse

    PARSER = argparse.ArgumentParser("Generate a template for a new Lambda Layer")
    PARSER.add_argument(
        "--yaml", required=False, action='store_true', help="Render in YAML"
    )
    PARSER.add_argument(
        "--create-stack", action='store_true', help="Creates a new stack with the generated template"
    )
    ARGS = PARSER.parse_args()
    if ARGS.yaml:
        print(TEMPLATE.to_yaml())
    else:
        print(TEMPLATE.to_json())
    if ARGS.create_stack:
        import boto3
        client = boto3.client('cloudformation')
        try:
            client.create_stack(
                StackName="LambdaLayers-PipelineRoles-platform",
                TemplateBody=TEMPLATE.to_json(),
                OnFailure='DELETE',
                Capabilities=['CAPABILITY_NAMED_IAM'],
                Tags=[
                    {
                        'Key': '20-business:department',
                        'Value': 'PlatformEngineering'
                    }
                ]
            )
        except Exception as e:
            print(e)


