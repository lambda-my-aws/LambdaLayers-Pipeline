from troposphere import (

    Template,
    Parameter,
    Output
)
from troposphere import (
    AWS_ACCOUNT_ID,
    AWS_STACK_NAME,
    AWS_REGION
)
from troposphere import (
    Select,
    GetAtt,
    Split,
    Ref,
    Sub
)
from troposphere import (
    Condition,
    Equals,
    Not,
    If
)
from troposphere.codepipeline import (
    Pipeline,
    Stages,
    Actions,
    ActionTypeId,
    OutputArtifacts,
    InputArtifacts,
    ArtifactStore,
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


def use_github_source(**kwargs):
    config = kwargs['Configuration']
    for key in ['Repo', 'Branch', 'Owner', 'OAuthToken']:
        if not key in config.keys():
            raise AttributeError(f'GitHub source requires {key}')
        elif not isinstance(config[key], (Ref, Sub, GetAtt, str)):
            raise TypeError(f'{key} has to be of type', Ref, Sub, GetAtt, str)

    action = ActionTypeId(
        Category="Source",
        Owner="ThirdParty",
        Provider="GitHub",
        Version="1"
    )
    config = kwargs
    config['PollForSourceChanges']: False
    return (action, config)


def use_codecommit_source(**kwargs):
    config = kwargs['Configuration']
    for key in ['RepositoryName', 'BranchName']:
        if not key in config.keys():
            raise AttributeError(f'GitHub source requires {key}')
        elif not isinstance(config[key], (Ref, Sub, GetAtt, str)):
            raise TypeError(f'{key} has to be of type', Ref, Sub, GetAtt, str)
    action = ActionTypeId(
        Category="Source",
        Owner="AWS",
        Provider="CodeCommit",
        Version="1"
    )
    return (action, config)


def set_source_action(output_artifacts, **kwargs):
    if 'UseGitHub' in kwargs.keys() and kwargs['UseGitHub']:
        action_config = use_github_source(**kwargs)
    elif 'UseCodeCommit' in kwargs.keys() and kwargs['UseCodeCommit']:
        action_config = use_codecommit(**kwargs)

    action = Actions(
        Name="SourceAction",
        ActionTypeId=action_config[0],
        Configuration=action_config[1],
        OutputArtifacts=output_artifacts,
        RunOrder="1"
    )
    return action


def set_build_action(input_artifacts, output_artifacts, build_project_stack, **kwargs):
    """
    """
    action = Actions(
        Name="BuildLayer",
        InputArtifacts=input_artifacts,
        ActionTypeId=ActionTypeId(
            Category="Build",
            Owner="AWS",
            Version="1",
            Provider="CodeBuild"
        ),
        Configuration={
            'ProjectName' : Sub(
                '${{{build_project_stack.title}}}-BuildProject-Name'
                )
        },
        OutputArtifacts=output_artifacts,
        RunOrder="1"
    )
    return action


def set_stage(name, actions):
    """
    """
    stage = Stages(
        Name=name,
        Actions=actions
    )
    return stage


def pipeline_build(stages, **kwargs):
    """
    returns:
        Pipeline
    """
    pipeline = Pipeline(
        "LayerPipeline",
        RestartExecutionOnUpdate=True,
        RoleArn='arn:aws:iam:::role/test',
        Stages=stages,
        ArtifactStore=ArtifactStore(
            Type="S3",
            Location="bucket"
        )
    )
    return pipeline


TEMPLATE = Template()
SOURCE_OUTPUT_ARTIFACT = OutputArtifacts(
    Name="BuildSource"
)
SOURCE_OUTPUTS = [SOURCE_OUTPUT_ARTIFACT]
SOURCE_STAGE_ACTION = set_source_action(
    SOURCE_OUTPUTS,
    UseGitHub=True,
    Configuration={
        'Repo': 'test',
        'Branch': 'toto',
        'Owner': 'me',
        'OAuthToken': 'token'
    }
)
SOURCE_STAGE = set_stage('Source', [SOURCE_STAGE_ACTION])
BUILD_INPUT_ARTIFACT = InputArtifacts(
    Name="BuildSource"
)
BUILD_INPUTS = [BUILD_INPUT_ARTIFACT]
BUILD_OUTPUT_ARTIFACT = OutputArtifacts(
    Name="BuildArtifact"
)
BUILD_OUTPUTS = [BUILD_OUTPUT_ARTIFACT]


PIPELINE = pipeline_build(
    [
        SOURCE_STAGE
    ]
)
TEMPLATE.add_resource(PIPELINE)

if __name__ == '__main__':
    import argparse
    import sys
    PARSER = argparse.ArgumentParser("Generate a template to create a new pipeline for Lambda Layers")
    PARSER.add_argument(
        "--json", required=False, action='store_true', help="Render in JSON"
    )
    PARSER.add_argument(
        '--layer-name', required=False, help="The name of the lambda layer to create the pipeline for"
    )
    ARGS = PARSER.parse_args()
    if ARGS.json:
        print(TEMPLATE.to_json())
    else:
        print(TEMPLATE.to_yaml())
