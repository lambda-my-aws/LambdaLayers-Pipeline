#!/usr/bin/env python

from urllib.request import build_opener, HTTPHandler, Request
import json
import logging
import signal
import boto3

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def create_initial_branch(repository_name, branch_name='master'):
    """
    Function to create a first commit to initialize a branch in a brand new codecommit repository
    """
    try:
        client = boto3.client('codecommit')
        commit = client.put_file(
            repositoryName=repository_name,
            branchName=branch_name,
            commitMessage='Initial commit to initialize the repository',
            filePath='README.md',
            fileContent='EDIT ME'
        )
        LOGGER.info(commit['commitId'])
        return (True, commit['commitId'])
    except Exception as e:
        LOGGER.info(e)
        return (False, e)



def lambda_handler(event, context):
    """
    Lambda Functio Handler
    """
    '''Handle Lambda event from AWS'''
    # Setup alarm for remaining runtime minus a second
    if event['RequestType'] == 'Create':
        if not 'RepositoryName' in event['ResourceProperties'].keys():
            send_response(
                event,
                context,
                "FAILED",
                {
                    "Message": "RepositoryName needs to be specified"
                }
            )
        commit = create_initial_branch(
            event['ResourceProperties']['RepositoryName']
        )
        if commit[0]:
            send_response(
                event,
                context,
                "SUCCESS",
                {
                    "Message": "Resource creation successful!"
                }
        )
        else:
            send_response(
                event,
                context,
                "FAILURE",
                {
                    "Message": commit[1]
                }
            )
    elif event['RequestType'] == 'Update':
        send_response(
            event,
            context,
            "SUCCESS",
            {
                "Message": "Resource update successful!"
            }
        )
    elif event['RequestType'] == 'Delete':
        send_response(
            event,
            context,
            "SUCCESS",
            {
                "Message": "Resource deletion successful!"
            }
        )
    else:
        LOGGER.info('FAILED!')
        send_response(
            event,
            context,
            "FAILED",
            {
            "Message": "Unexpected event received from CloudFormation"
            }
        )


def send_response(event, context, response_status, response_data):
    '''Send a resource manipulation status response to CloudFormation'''
    response_body = json.dumps(
        {
            "Status": response_status,
            "Reason": "See the details in CloudWatch Log Stream: " + context.log_stream_name,
            "PhysicalResourceId": context.log_stream_name,
            "StackId": event['StackId'],
            "RequestId": event['RequestId'],
            "LogicalResourceId": event['LogicalResourceId'],
        "Data": response_data
        }
    )

    bin_data = response_body.encode('UTF-8')
    opener = build_opener(HTTPHandler)
    request = Request(event['ResponseURL'], data=bin_data)
    request.add_header('Content-Type', '')
    request.add_header('Content-Length', len(response_body))
    request.get_method = lambda: 'PUT'
    response = opener.open(request)
