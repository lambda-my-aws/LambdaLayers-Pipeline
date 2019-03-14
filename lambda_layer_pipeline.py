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

from troposphere.codepipeline import (
    Pipeline, Stages, Actions, ActionTypeId,
    OutputArtifacts, InputArtifacts, ArtifactStore,
    DisableInboundStageTransitions
)

from troposphere.codebuild import (
    Environment,
    Source,
    Project,
    Artifacts
)

from troposphere.cloudformation import AWSCustomObject
from troposphere.codecommit import Repository as Repo


TEMPLATE = Template()
TEMPLATE.add_description("Generate a CICD pipeline for a new Lambda Layer")

# Parameters - need to have a value at CFN stack Creation

layer_name = TEMPLATE.add_parameter(Parameter(
    "LambdaLayerName",
    Type="String",
    AllowedPattern="[a-z]*"
))


lambda_layer_cfn_generator_function = TEMPLATE.add_parameter(Parameter(
    "LambdaLayerCloudFormationGeneratorFunctionName",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="LambdaLayers-GeneratorFunction-Name"

))

codecommit_init_function = TEMPLATE.add_parameter(Parameter(
    "CodeCommitInitFunction",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="CodePipelineTools-CodeCommitInit-Arn"

))

layers_dest_bucket = TEMPLATE.add_parameter(Parameter(
    "DestArtifactsBucket",
    Description="Bucket in which store the built Lambda Layer",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="LambdaLayers-ArtifactsBucket"
))


lambda_layer_build_role_arn = TEMPLATE.add_parameter(Parameter(
    "LambdaLayersCodeBuildRoleArn",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="LambdaLayersPipeline-CodeBuildRoleArn"
))


lambda_layer_pipeline_role_arn = TEMPLATE.add_parameter(Parameter(
    "LambdaLayersCodePipelineRoleArn",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="LambdaLayersPipeline-CodePipelineRoleArn"
))


lambda_layer_cfn_role_arn = TEMPLATE.add_parameter(Parameter(
    "LambdaLayersCloudFormationRoleArn",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="LambdaLayersPipeline-CloudFormationRoleArn"
))


# Resources

codecommit_repository = TEMPLATE.add_resource(Repo(
    "LambdaLayerRepository",
    RepositoryDescription=Sub('Repository for ${LambdaLayerName}'),
    RepositoryName=Sub('layer-${LambdaLayerName}')
))


class LambdaFunctionCall(AWSCustomObject):
    resource_type = "AWS::CloudFormation::CustomResource"
    props = {
        'ServiceToken': (str, True),
        'RepositoryName': (str, True),
        'BranchName': (str, False)
    }

codecommit_init = TEMPLATE.add_resource(
    LambdaFunctionCall(
        "CodeCommitInitRepo",
        DependsOn=[
            codecommit_repository.title
        ],
        DeletionPolicy='Retain',
        RepositoryName=GetAtt(codecommit_repository, 'Name'),
        ServiceToken=Ref(codecommit_init_function)
    )
)


codebuild_project = TEMPLATE.add_resource(
    Project(
        "LayerBuildProject",
        DependsOn=[
            codecommit_repository.title,
            codecommit_init.title
        ],
        Source=Source(Type='CODEPIPELINE'),
        Artifacts=Artifacts(
            Type='CODEPIPELINE',
            Packaging="ZIP",
            NamespaceType="NONE"
        ),
        Environment=Environment(
            ComputeType='BUILD_GENERAL1_SMALL',
            Image='aws/codebuild/python:3.7.1',
            Type='LINUX_CONTAINER',
            EnvironmentVariables=[]
    ),
        Name=Sub('${LambdaLayerName}-BuildProject'),
        ServiceRole=Ref(lambda_layer_build_role_arn)
    )
)

import json

pipeline = TEMPLATE.add_resource(
    Pipeline(
        "LayerPipeline",
        RestartExecutionOnUpdate=True,
        DependsOn=[
            codecommit_repository.title,
            codecommit_init.title
        ],
        RoleArn=Ref(lambda_layer_pipeline_role_arn),
        Stages=[
            Stages(
                Name="Source",
                Actions=[
                    Actions(
                        Name="SourceAction",
                        ActionTypeId=ActionTypeId(
                            Category="Source",
                            Owner="AWS",
                            Provider="CodeCommit",
                            Version="1",
                        ),
                        Configuration={
                            'RepositoryName': GetAtt(codecommit_repository, 'Name'),
                            'BranchName': 'master',
                            'PollForSourceChanges': False
                        },
                        OutputArtifacts=[
                            OutputArtifacts(
                                Name="BuildSource"
                            )
                        ],
                        RunOrder="1"
                    )
                ]
            ),
            Stages(
                Name="Build",
                Actions=[
                    Actions(
                        Name="BuildLayer",
                        InputArtifacts=[
                            InputArtifacts(
                                Name="BuildSource"
                            )
                        ],
                        ActionTypeId=ActionTypeId(
                            Category="Build",
                            Owner="AWS",
                            Version="1",
                            Provider="CodeBuild"
                        ),
                        Configuration={
                            'ProjectName' : Ref(codebuild_project)
                        },
                        OutputArtifacts=[
                            OutputArtifacts(
                                Name="LayerZip"
                            )
                        ],
                        RunOrder="1"
                    )
                ]
            ),
            Stages(
                Name="Prepare",
                Actions=[
                    Actions(
                        Name="GenerateCfnTemplate",
                        InputArtifacts=[
                            InputArtifacts(
                                Name="LayerZip"
                            )
                        ],
                        ActionTypeId=ActionTypeId(
                            Category="Invoke",
                            Owner="AWS",
                            Version="1",
                            Provider="Lambda"
                        ),
                        Configuration={
                            'FunctionName': Ref(lambda_layer_cfn_generator_function),
                            'UserParameters': Ref(layer_name)
                        },
                        OutputArtifacts=[
                            OutputArtifacts(
                                Name="GeneratedTemplate"
                            )
                        ],
                        RunOrder="1"
                    )
                ]
            ),
            Stages(
                Name="Deploy",
                Actions=[
                    Actions(
                        Name="DeployLayer",
                        ActionTypeId=ActionTypeId(
                            Category="Deploy",
                            Owner="AWS",
                            Version="1",
                            Provider="CloudFormation"
                        ),
                        InputArtifacts=[
                            InputArtifacts(
                                Name="GeneratedTemplate"
                            )
                        ],
                        Configuration={
                            'StackName': Sub('LambdaLayers-layer-${LambdaLayerName}-platform'),
                            'ActionMode': 'CREATE_UPDATE',
                            'RoleArn': Ref(lambda_layer_cfn_role_arn),
                            'TemplatePath': 'GeneratedTemplate::tmp/template.json'
                        },
                        RunOrder="1"
                    )
                ]
            )
        ],
        ArtifactStore=ArtifactStore(
            Type="S3",
            Location=Ref(layers_dest_bucket)
        )
    )
)

TEMPLATE.add_output([
    Output(
        "LambdaLayerRepositoryCloneUrlHttp",
        Value=GetAtt(codecommit_repository, 'CloneUrlHttp')
    ),
    Output(
        "LambdaLayerRepositoryArn",
        Value=GetAtt(codecommit_repository, 'Arn')
    ),
    Output(
        "LambdaLayerRepositoryName",
        Value=GetAtt(codecommit_repository, 'Name')
    ),
    Output(
        "LambdaLayerBuildProjectName",
        Value=Ref(codebuild_project)
    ),
    Output(
        "LambdaLayerPipelineName",
        Value=Ref(pipeline)
    )
])

if __name__ == '__main__':
    import argparse
    import sys
    PARSER = argparse.ArgumentParser("Generate a template to create a new pipeline for Lambda Layers")
    PARSER.add_argument(
        "--yaml", required=False, action='store_true', help="Render in YAML"
    )
    PARSER.add_argument(
        "--create-stack", action='store_true', help="Creates a new stack with the generated template"
    )
    PARSER.add_argument(
        '--layer-name', required=False, help="The name of the lambda layer to create the pipeline for"
    )
    ARGS = PARSER.parse_args()
    if ARGS.create_stack and not ARGS.layer_name:
        print("Layer name is required to create the stack")
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
                StackName="LambdaLayers-%s-Pipeline-platform" % (ARGS.layer_name),
                TemplateBody=TEMPLATE.to_json(),
                Parameters=[
                    {
                        'ParameterKey': layer_name.title,
                        'ParameterValue': ARGS.layer_name
                    }
                ],
                TimeoutInMinutes=10,
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


