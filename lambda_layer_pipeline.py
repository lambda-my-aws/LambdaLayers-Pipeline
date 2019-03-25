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
from troposphere import (
    Condition,
    Equals,
    Not,
    If
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

from troposphere.codecommit import Repository as Repo
from common import (
    LambdaFunctionCall
)

TEMPLATE = Template()
TEMPLATE.add_description("Generate a CICD pipeline for a new Lambda Layer")

# Parameters - need to have a value at CFN stack Creation


CONDITIONS = {
    "UseCodeCommit": Equals(
        Ref(REPOSITORY_PROVIDER),
        "CodeCommit"
    ),
    "UseGitHub": Not(
        Condition("UseCodeCommit")
    )
}

for p in PARAMETERS:
    TEMPLATE.add_parameter(p, PARAMETERS[p])
for k in CONDITIONS:
    TEMPLATE.add_condition(k, CONDITIONS[k])
# Resources


RESOURCES = [
    codecommit_repository = Repo(
        "LambdaLayerRepository",
        Condition="UseCodeCommit",
        RepositoryDescription=Sub('Repository for ${LambdaLayerName}'),
        RepositoryName=Sub('layer-${LambdaLayerName}')
    )
    codecommit_init = LambdaFunctionCall(
        "CodeCommitInitRepo",
        Condition="UseCodeCommit",
        DeletionPolicy='Retain',
        RepositoryName=GetAtt(codecommit_repository, 'Name'),
        ServiceToken=Ref(codecommit_init_function)
    )
    codebuild_project = Project(
        "LayerBuildProject",
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
    pipeline = Pipeline(
        "LayerPipeline",
        RestartExecutionOnUpdate=True,
        RoleArn=Ref(lambda_layer_pipeline_role_arn),
        Stages=[
            If(
                "UseCodeCommit",
                CODECOMMIT_STAGE,
                GITHUB_STAGE
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
        Value=If(
            "UseCodeCommit",
            GetAtt(codecommit_repository, 'CloneUrlHttp'),
            Ref(REPOSITORY_NAME)
        )
    ),
    Output(
        "LambdaLayerRepositoryArn",
        Value=If(
            "UseCodeCommit",
            GetAtt(codecommit_repository, 'Arn'),
            Ref(REPOSITORY_NAME)
        )
    ),
    Output(
        "LambdaLayerRepositoryName",
        Value=If(
            "UseCodeCommit",
            GetAtt(codecommit_repository, 'Name'),
            Ref(REPOSITORY_NAME)
        )
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


