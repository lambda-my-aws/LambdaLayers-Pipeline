#!/usr/bin/env python


from troposphere import Template
from cloudformation.outputs import output_no_export
from helpers.devtools.pipeline import (
    SourceAction,
    BuildAction,
    DeployAction,
    InvokeAction,
    CodePipeline
)
source = SourceAction(
    name="GitRepoXyZ",
    provider='GitHub',
    config={
        'Repo': 'somerepo',
        'Branch': 'master',
        'Owner': 'me',
        'OAuthToken': '12345'
    }
)

build_actions = []
builds_projects = ['python37', 'python36']
for project in builds_projects:
    build_actions.append(BuildAction(
        project,
        source.outputs,
        project
    ))

build_outputs = []
for action in build_actions:
    build_outputs += action.outputs

merge_action = BuildAction(
    'MergeAction',
    build_outputs,
    'buil-merge-project'
)

invoke = InvokeAction(
    'GenerateCfnTemplate',
    source.outputs,
    'nameofthefunction',
    UserParameters='layer-abcd'
)

input_name = source.outputs[0].Name
deploy = DeployAction(
    'DeployToCfn',
    build_actions[0].outputs,
    'CloudFormation',
    StackName='nameofthestack',
    RoleArn='roleforcloudformation',
    TemplatePath=f'{input_name}::tmp/template.json'
)

stages = [
    ('Source', [source]),
    ('BuildLayers', build_actions),
    ('MergeLayers', [merge_action]),
    ('GenerateCfnTemplate', [invoke]),
    ('DeployWithCfn', [deploy]),
]

pipe = CodePipeline(
    'Pipeline',
    'somerole',
    'somes3bucket',
    stages
)

template = Template()
template.add_resource(pipe)
template.add_output(output_no_export(pipe))
print(template.to_yaml())
