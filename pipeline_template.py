#!/usr/bin/env python
"""
Script to generate a CodePipeline pipeline with
- Source from GitHub
- Build Stage with 2 actions
- Lambda invoke
- CloudFormation deploy
"""

from troposphere import (
    ImportValue,
    Parameter,
    Template,
    Output,
    Select,
    Ref,
    Sub
)
from troposphere.codepipeline import (
    OutputArtifacts,
    InputArtifacts
)
from troposphere.codebuild import Project
from cloudformation.resources.iam.pipeline_role import pipelinerole_build
from cloudformation.resources.devtools.pipeline import (
    use_github_source,
    use_codecommit_source,
    set_source_action,
    set_build_action,
    set_deploy_action,
    set_invoke_action,
    set_stage,
    pipeline_build
)
from cloudformation import get_resource_type
import argparse

def increment(x):
    xx = bytes(x, 'utf-8')
    s = bytes([xx[0] + 1])
    s = str(s)
    return s[2]

INC = lambda x: increment(x)

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
## PARAMETERS ##

BUCKET_NAME = TEMPLATE.add_parameter(Parameter(
    'BucketName',
    Type="String",
    AllowedPattern="[a-z]+"
))
LAYER_NAME = TEMPLATE.add_parameter(Parameter(
    'LayerName',
    Type="String",
    AllowedPattern="[a-z]+"
))
PIPELINE_FUNCTION = TEMPLATE.add_parameter(Parameter(
    'TemplateGeneratorFunction',
    Type="String"
))
TOKEN = TEMPLATE.add_parameter(Parameter(
    'GitHubToken',
    Type="String",
    NoEcho=True
))
BUILD_STACKS = TEMPLATE.add_parameter(Parameter(
    'BuildStacks',
    Type="CommaDelimitedList"
))

ROLE = TEMPLATE.add_resource(
    pipelinerole_build(
        Bucket=Ref(BUCKET_NAME),
        UseCloudformation=True,
        UseCodeBuild=True
    )
)

## SOURCE_STAGE ##
SOURCE_OUTPUT_ARTIFACT = OutputArtifacts(
    Name="BuildSource"
)
SOURCE_OUTPUTS = [SOURCE_OUTPUT_ARTIFACT]
SOURCE_STAGE_ACTION = set_source_action(
    SOURCE_OUTPUTS,
    UseGitHub=True,
    Configuration={
        'Repo': 'layer-troposphere',
        'Branch': 'master',
        'Owner': 'lambda-my-aws',
        'OAuthToken': Ref(TOKEN)
    }
)
SOURCE_STAGE = set_stage('Source', [SOURCE_STAGE_ACTION])
## END ##
## BUILD STAGE ##

BUILD_INPUT_ARTIFACT = InputArtifacts(
    Name="BuildSource"
)
BUILD_INPUTS = [BUILD_INPUT_ARTIFACT]
BUILD_ACTIONS = []
ACOUNT = 'A'
NCOUNT = 0
BUILD_STACKS = []
if ARGS.build_stacks:
    BUILD_STACKS = ARGS.build_stacks
for build in BUILD_STACKS:
    resource_type = get_resource_type(Project)
    BUILD_ACTIONS.append(
        set_build_action(
            BUILD_INPUTS,
            [
                OutputArtifacts(Name=f'BuildOutput{ACOUNT}')
            ],
            ImportValue(Sub(f'${{Stack}}-{resource_type}-Name', Stack=Select(NCOUNT, Ref(BUILD_STACKS))))
        )
    )
    COUNT = INC(ACOUNT)
    NCOUNT += 1
BUILD_STAGE = set_stage('Build', BUILD_ACTIONS)
## END ##
## DEPLOY STAGE ##

DEPLOY_INPUTS = [InputArtifacts(Name="InputForCfn")]
DEPLOY_STAGE_ACTION_CFN = set_deploy_action(
    DEPLOY_INPUTS,
    DeployProvider='Cloudformation',
    CloudformationRole='arn:aws:iam::123456789012:role/toto',
    StackName=Ref(LAYER_NAME),
    TemplatePath="CfnTemplate::template.json"
)
DEPLOY_STAGE = set_stage('Deploy', [DEPLOY_STAGE_ACTION_CFN])
## END DEPLOY ##
## INVOKE STAGE ##
INVOKE_STAGE_ACTION = set_invoke_action([InputArtifacts(Name="BuildOutput")], [OutputArtifacts(Name='CfnTemplate')], FunctionName=Ref(PIPELINE_FUNCTION))
INVOKE_STAGE = set_stage('Invoke', [INVOKE_STAGE_ACTION])

## END INVOKE ##

### END STAGES ###

PIPELINE = pipeline_build(
    [
        SOURCE_STAGE,
        BUILD_STAGE,
        INVOKE_STAGE,
        DEPLOY_STAGE
    ],
    ROLE,
    Ref(BUCKET_NAME)
)

TEMPLATE.add_resource(PIPELINE)
if ARGS.json:
    print(TEMPLATE.to_json())
else:
    print(TEMPLATE.to_yaml())

