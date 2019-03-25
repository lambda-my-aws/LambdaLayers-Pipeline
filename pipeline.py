from troposphere import (
    Template,
    Parameter,
    Output
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
from cloudformation.resources.devtools.pipeline import (
    use_github_source,
    use_codecommit_source,
    set_source_action,
    set_build_action,
    set_stage,
    pipeline_build
)
import argparse

PARSER = argparse.ArgumentParser("Generate a template to create a new pipeline for Lambda Layers")
PARSER.add_argument(
    "--json", required=False, action='store_true', help="Render in JSON"
)
PARSER.add_argument(
    '--layer-name', required=False, help="The name of the lambda layer to create the pipeline for"
)
PARSER.add_argument(
    '--build-stacks', action='append', required=False,
    help="Name of the stacks which contain a valid build project for that pipeline"
)
ARGS = PARSER.parse_args()
TEMPLATE = Template()
TEMPLATE.set_description('Pipeline template')
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
BUILD_PROJECT_STACK = Parameter('BuildProjectStack', Type="CommaDelimitedList")
BUILD_STAGE_ACTION_A = set_build_action(
    BUILD_INPUTS,
    BUILD_OUTPUTS,
    BUILD_PROJECT_STACK
)
BUILD_STAGE_ACTION_B = set_build_action(
    BUILD_INPUTS,
    BUILD_OUTPUTS,
    BUILD_PROJECT_STACK
)
BUILD_STAGE = set_stage('Build', [BUILD_STAGE_ACTION_A, BUILD_STAGE_ACTION_B])
PIPELINE = pipeline_build(
    [
        SOURCE_STAGE,
        BUILD_STAGE
    ]
)
TEMPLATE.add_resource(PIPELINE)
if ARGS.json:
    print(TEMPLATE.to_json())
else:
    print(TEMPLATE.to_yaml())
