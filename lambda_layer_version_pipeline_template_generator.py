#!/usr/bin/env python
"""

Lambda Function / Script that allows to generate a CFN template
to create / update a new Lambda Layer Version

"""
from zipfile import ZipFile
from troposphere import (
    Template,
    Output,
    Ref
)
from troposphere.awslambda import (
    LayerVersion,
    Content
)
from troposphere.ssm import (
    Parameter as SSMParam
)
import boto3


def codepipeline_failure_report(job_id):
    """
    Reports a job failure to Codepipeline
    """
    client = boto3.client(
        'codepipeline')
    client.put_job_success_result(
        jobId=job_id,
        currentRevision={
            'revision': "1",
            'changeIdentifier': "1"
        }
    )


def codepipeline_success_report(job_id):
    """
    Returns a job success to CodePipeline
    """
    client = boto3.client(
        'codepipeline')
    client.put_job_success_result(
        jobId=job_id,
        currentRevision={
            'revision': "1",
            'changeIdentifier': "1"
        }
    )


def create_artifact(template, key_file_name):
    """
    Writes the generated template file and Zips it to be used by CFN in the Pipeline
    Path matters for CodePipeline to feed the right template file to CFN
    """
    with open('/tmp/template.json', 'w') as template_t:
        template_t.write(template.to_json())
    zip_path = '/tmp/' + key_file_name
    with ZipFile(zip_path, 'w') as zip_fd:
        zip_fd.write('/tmp/template.json')


def init_template(description="Troposphere generated CFN template"):
    """
    Creates a new troposphere template and initializes it with a Description
    """
    template = Template()
    template.add_description(description)
    return template


def create_lambda_layer_version(resource_name, layer_name,
                                s3_bucket, s3_key,
                                compatible_runtimes=["python3.7"]):
    """
    Creates a new Lambda Layer object for the CFN template using the
    CodePipeline info to identify the location of the new Lambda Layer code
    """
    return LayerVersion(
        resource_name,
        Description="LambdaLayerVersion for %s" % (layer_name),
        DeletionPolicy="Retain",
        LayerName=layer_name,
        CompatibleRuntimes=compatible_runtimes,
        Content=Content(
            S3Bucket=s3_bucket,
            S3Key=s3_key
        )
    )


def generate_template(description, layer_name, layer_s3_bucket, layer_s3_key, job_id=None, ssm=False):
    """
    Function to generate the Troposphere template
    """
    template = init_template(description)
    resource_name = "LambdaLayerVersion"
    if job_id is str:
        resource_name += job_id.split('-')[0]
        layer_version = create_lambda_layer_version(
            resource_name,
            layer_name,
            layer_s3_bucket,
            layer_s3_key,
            job_id
        )
    else:
        layer_version = create_lambda_layer_version(
            resource_name,
            layer_name,
            layer_s3_bucket,
            layer_s3_key,
        )
    template.add_resource(
        layer_version
    )
    if ssm:
        template.add_resource(SSMParam(
            "SsmLambdaLayerArn",
            Name='LambdaLayers-%s-Arn' % (layer_name),
            Value=Ref(layer_version),
            Type="String"
        ))
    template.add_output([
        Output(
            "LambdaLayerVersion",
            Value=Ref(layer_version)
        )
    ])
    return template


def lambda_handler(event, context):
    """
    Lambda function handler - receives the event from CodePipeline
    and generates the CFN template + Uploads the artifact with the template.
    """

    try:
        data = event['CodePipeline.job']['data']
        dest_s3_location = data["outputArtifacts"][0]['location']['s3Location']
        dest_s3_key = dest_s3_location['objectKey']
        dest_s3_bucket = dest_s3_location['bucketName']

        layer_s3_location = data["outputArtifacts"][0]['location']['s3Location']
        layer_s3_key = layer_s3_location['objectKey']
        layer_s3_bucket = layer_s3_location['bucketName']


        job_id = event["CodePipeline.job"]['id']

        layer_name = data['actionConfiguration']['configuration']['UserParameters']
        template = generate_template(
            "Lambda Generated Template for CodePipeline for Deploy steps",
            layer_name,
            layer_s3_bucket,
            layer_s3_key,
            job_id,
            ssm=True
        )
        key_file_name = dest_s3_key.split('/')[-1]
        create_artifact(template, key_file_name)

        client = boto3.client('s3')
        client.put_object(
            ACL='private',
            Bucket=dest_s3_bucket,
            Key=dest_s3_key,
            Body=open('/tmp/%s' % (key_file_name), 'rb')
        )
        return codepipeline_success_report(job_id)

    except Exception as e:
        print(e)
        return codepipeline_failure_report(job_id)


if __name__ == '__main__':

    import argparse
    PARSER = argparse.ArgumentParser("Generate a template for a new Lambda Layer")
    PARSER.add_argument("--layer-name", required=True, help="Name of the layer")
    PARSER.add_argument(
        "--s3-bucket", required=True,
        help="Name of the s3 bucket that contains the Layer code"
    )
    PARSER.add_argument(
        "--s3-key", required=True, help="Name of the s3 key that contains the Layer code"
    )
    PARSER.add_argument(
        "--yaml", required=False, action='store_true', help="Render in YAML"
    )
    PARSER.add_argument(
        "--create-ssm", action='store_true', help="Creates SSM resource with the ARN of the Lambda Layer"
    )
    PARSER.add_argument(
        "--create-stack", action='store_true', help="Creates SSM resource with the ARN of the Lambda Layer"
    )
    ARGS = PARSER.parse_args()

    if not ARGS.create_ssm:
        TEMPLATE = generate_template(
            "Manually generated template for a new Lambda Layer",
            ARGS.layer_name,
            ARGS.s3_bucket,
            ARGS.s3_key,
        )
    else:
        TEMPLATE = generate_template(
            "Manually generated template for a new Lambda Layer",
            ARGS.layer_name,
            ARGS.s3_bucket,
            ARGS.s3_key,
            ssm=True
        )
    if ARGS.yaml:
        print(TEMPLATE.to_yaml())
    else:
        print(TEMPLATE.to_json())


    if ARGS.create_stack:
        client = boto3.client('cloudformation')
        try:
            client.create_stack(
                StackName="LambdaLayers-layer-%s-platform" % (ARGS.layer_name),
                TemplateBody=TEMPLATE.to_json(),
                OnFailure='DELETE',
                Tags=[
                    {
                        'Key': '20-business:department',
                        'Value': 'PlatformEngineering'
                    }
                ]
            )
        except Exception as e:
            print(e)

