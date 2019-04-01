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
from cloudformation.filters.patterns import IAM_ROLE_ARN
from troposphere.codebuild import Project
from helpers.iam.roles.pipeline_role import pipelinerole_build
from helpers.devtools.pipeline import (
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
    Type="String"
))
LAYER_NAME = TEMPLATE.add_parameter(Parameter(
    'LayerName',
    Type="String",
    AllowedPattern="[a-z-]+"
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
BUILD_STACKS_PARAM = TEMPLATE.add_parameter(Parameter(
    'BuildStacks',
    Type="CommaDelimitedList"
))

ROLE = TEMPLATE.add_resource(
    pipelinerole_build(
        Bucket=Sub('arn:aws:s3:::${BucketName}/*'),
        UseCloudformation=True,
        UseCodeBuild=True,
        UseLambda=True
    )
)
MERGE_STACK_NAME = TEMPLATE.add_parameter(Parameter(
    'MergeStackName',
    Type="String"
))
REPOSITORY_NAME = TEMPLATE.add_parameter(Parameter(
    'RepositoryName',
    Type="String"
))
GITHUB_OWNER = TEMPLATE.add_parameter(Parameter(
    'GithubOwner',
    Type="String"
))
BRANCH_NAME = TEMPLATE.add_parameter(Parameter(
    'BranchName',
    Type="String"
))
CFN_ROLE_ARN = TEMPLATE.add_parameter(Parameter(
    'CloudformationRoleArn',
    Type="String",
    AllowedPattern=IAM_ROLE_ARN
))

## SOURCE_STAGE ##
SOURCE_OUTPUT_ARTIFACT = OutputArtifacts(
    Name="BuildSource"
)
SOURCE_OUTPUTS = [SOURCE_OUTPUT_ARTIFACT]
SOURCE_STAGE_ACTION = set_source_action(
    SOURCE_OUTPUTS,
    UseGitHub=True,
    Configuration={
        'Repo': Ref(REPOSITORY_NAME),
        'Branch': Ref(BRANCH_NAME),
        'Owner': Ref(GITHUB_OWNER),
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
MERGE_INPUTS = []
if ARGS.build_stacks:
    BUILD_STACKS = ARGS.build_stacks
for build in BUILD_STACKS:
    resource_type = get_resource_type(Project)
    BUILD_ACTIONS.append(
        set_build_action(
            f'BuildLayer{ACOUNT}',
            BUILD_INPUTS,
            [
                OutputArtifacts(Name=f'BuildOutput{ACOUNT}')
            ],
            ImportValue(Sub(f'${{Stack}}-{resource_type}-Name', Stack=Select(NCOUNT, Ref(BUILD_STACKS_PARAM))))
        )
    )
    MERGE_INPUTS.append(InputArtifacts(Name=f'BuildOutput{ACOUNT}'))
    ACOUNT = INC(ACOUNT)
    NCOUNT += 1
BUILD_STAGE = set_stage('Build', BUILD_ACTIONS)
## END ##
## MERGE STAGE ##
MERGE_ACTIONS = [set_build_action('MergeLayers', MERGE_INPUTS, [OutputArtifacts(Name="LayersMerged")], ImportValue(Sub(f'${{MergeStackName}}-{resource_type}-Name')))]
MERGE_STAGE = set_stage('MergeLayers', MERGE_ACTIONS)
## END MERGE ##
## INVOKE STAGE ##
INVOKE_STAGE_ACTION = set_invoke_action(
    [InputArtifacts(
        Name="LayersMerged")],
    [OutputArtifacts(Name='CfnTemplate')],
    FunctionName=Ref(PIPELINE_FUNCTION)
)
INVOKE_STAGE = set_stage('Invoke', [INVOKE_STAGE_ACTION])

## END INVOKE ##
## DEPLOY STAGE ##
DEPLOY_INPUTS = [InputArtifacts(Name="CfnTemplate")]
DEPLOY_STAGE_ACTION_CFN = set_deploy_action(
    DEPLOY_INPUTS,
    DeployProvider='Cloudformation',
    CloudformationRole='arn:aws:iam::234354856264:role/cfnonly',
    StackName=Ref(LAYER_NAME),
    TemplatePath="CfnTemplate::template.json"
)
DEPLOY_STAGE = set_stage('Deploy', [DEPLOY_STAGE_ACTION_CFN])
## END DEPLOY ##

### END STAGES ###

PIPELINE = pipeline_build(
    [
        SOURCE_STAGE,
        BUILD_STAGE,
        MERGE_STAGE,
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


