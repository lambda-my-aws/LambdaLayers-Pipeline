#!/usr/bin/env python

from troposphere import Tags
from ozone.templates.awslambdalayer_pipeline import template as pipeline
from ozone.handlers.lambda_tools import check_params_exist
from ozone.handlers.stack_manage import create_update_stack


def template_build(event):
    """
    Args:
      event: lambda function event
    Returns:
      template Template()
    """
    template = pipeline(**event)
    return template


def lambda_handler(event, context=None):
    """
    Args:
      event: Lambda event call parameters
      context: Lambda event context (user specified)
    Returns based on arguments:
      template Template()
      JSON String of the rendered template
      AWS CloudFormation StackName
    """
    template_uri = None
    required_params = [
        'TemplatesBucket',
        'CloudformationRoleArn', 'StackTags', 'Region', 'SnsTopics',
        'TemplateArgs'
    ]
    assert check_params_exist(required_params, event)
    template = template_build(event['TemplateArgs'])
    template_body = template.to_yaml()
    print(template_body)
    if len(template_body) > 51200:
        template_uri = create_template_in_s3(event['TemplatesBucket'], event['BucketName'], template_body)
    cfn_args = {
        'StackName': f'pipeline-layer-{event["TemplateArgs"]["LayerName"]}',
        'RoleARN': event['CloudformationRoleArn'],
        'OnFailure' : 'DELETE',
        'EnableTerminationProtection': True,
        'NotificationARNs': event['SnsTopics'],
        'Tags': Tags(event['StackTags']).to_dict(),
        'Capabilities': ['CAPABILITY_IAM'],
        'Parameters': [
            {
                'ParameterKey': "GitHubOAuthToken",
                'ParameterValue': event['TemplateArgs']['OAuthToken']
            }
        ]
    }
    if template_uri is not None and tempalte_uri[0]:
        cfn_args['TemplateURL'] = template_uri[1]
    else:
        cfn_args['TemplateBody'] = template_body
    try:
        response = create_update_stack(event['Region'], **cfn_args)
        return response
    except Exception as error:
        print(error)
        return {'StackId': None}


if __name__ == '__main__':
    from argparse import ArgumentParser
    PARSER = ArgumentParser()
    PARSER.add_argument('--templates-bucket', required=True)
    PARSER.add_argument('--artifacts-bucket', required=True)
    PARSER.add_argument('--role-arn', required=True)
    PARSER.add_argument('--sns-topics', required=True, action='append')
    PARSER.add_argument('--region', required=True)
    PARSER.add_argument('--token', required=True)
    ARGS = PARSER.parse_args()

    TEMPLATE_ARGS = {
        'Source' : {
            'Provider': 'GitHub',
            'Config': {
                'Repo': 'ozone',
                'Owner': 'lambda-my-aws',
                'Branch': 'master'
            }
        },
        'OAuthToken': ARGS.token,
        'CloudformationRoleArn': ARGS.role_arn,
        'LayerBuildProjects': [
            'lambdalayers-buildproject-python371',
            'lambdalayers-buildproject-python365'
        ],
        'LayersMergeProject': 'lambdalayers-buildproject-mergelayers',
        'LayerName': 'ozone',
        'GeneratorFunctionName': 'function-layertemplatebuilder',
        'BucketName': ARGS.artifacts_bucket
    }
    EVENT = {
        'TemplatesBucket': ARGS.templates_bucket,
        'CloudformationRoleArn': ARGS.role_arn,
        'SnsTopics': ARGS.sns_topics,
        'Region': ARGS.region,
        'StackTags': {'10-technical:region': 'eu-west-1'}
    }
    EVENT['TemplateArgs'] = TEMPLATE_ARGS
    response = lambda_handler(EVENT, None)
