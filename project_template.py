#!/usr/bin/env python
"""
Script to create a CodeBuild project
"""
from troposphere import (
    Template,
    Parameter
)
from troposphere import (
    Ref
)
from cloudformation.outputs import (
    output_with_export,
    output_no_export
)
from cloudformation.resources.devtools.buildproject import (
    role_build,
    get_build_project
)
from cloudformation.tags.s3 import s3_default_tags
from cloudformation.policies import AWS_LAMBDA_BASIC_EXEC
from cloudformation.policies.role import role_trust_policy
from cloudformation.tags.codebuild import codebuild_default_tags
from codebuild.runtime import generate_runtime_mapping_and_parameters

TEAM_LANGUAGES= ['python', 'docker', 'base', 'node_js']

TEMPLATE = Template()
MAPPINGS_PARAMS = generate_runtime_mapping_and_parameters(
    TEAM_LANGUAGES
)
if not MAPPINGS_PARAMS[0]:
    exit(1)
RUNTIME_LANGUAGE = Parameter(
    "BuildRuntimeLanguage",
    Type="String",
    AllowedValues=MAPPINGS_PARAMS[2]
)
RUNTIME_VERSIONS = Parameter(
    "BuildRuntimeVersion",
    Type="String",
    AllowedValues=MAPPINGS_PARAMS[3]
)
TEMPLATE.add_parameter(RUNTIME_LANGUAGE)
TEMPLATE.add_parameter(RUNTIME_VERSIONS)
TEMPLATE.add_mapping('Languages', MAPPINGS_PARAMS[1])
BUCKET = TEMPLATE.add_parameter(Parameter(
    'PipelineBucket',
    Type="String",
    AllowedPattern="[a-z-]+"
))
ROLE = role_build(Ref(BUCKET))
PROJECT = get_build_project(
    ROLE,
    RUNTIME_LANGUAGE.title,
    RUNTIME_VERSIONS.title,
    **{
        '10-technical:team': 'PlatformEngineering',
        '10-technical:runtime_language' : Ref(RUNTIME_LANGUAGE),
        '10-technical:runtime_version' : Ref(RUNTIME_VERSIONS)
    }
)
TEMPLATE.add_resource(ROLE)
TEMPLATE.add_resource(PROJECT)
TEMPLATE.add_output(
    output_with_export(
        PROJECT, True,
        RunTimeLanguage=RUNTIME_LANGUAGE,
        RunTimeVersions=RUNTIME_VERSIONS
    )
)

print(TEMPLATE.to_yaml())
