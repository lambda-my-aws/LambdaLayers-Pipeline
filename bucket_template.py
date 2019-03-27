#!/usr/bin/env python
"""
Script to generate a S3 bucket for Pipeline Artifacts
"""
from troposphere import (
    Template,
    Parameter,
    Ref,
    Sub
)

from troposphere.ssm import (
    Parameter as SSMParam
)

from cloudformation.outputs import (
    output_no_export,
    output_with_export
)
from cloudformation.tags.s3 import s3_default_tags
from cloudformation.resources.s3.bucket import bucket_build
import argparse

PARSER = argparse.ArgumentParser("replica bucket with kms ey for encryption")
PARSER.add_argument(
    "--json", help="Render template in JSON", required=False,
    action='store_true'
)
ARGS = PARSER.parse_args()

TEMPLATE = Template()
TEMPLATE.set_description("S3 Bucket to which is replicated objects from another bucket")
BUCKET_NAME = TEMPLATE.add_parameter(Parameter(
    'S3BucketName',
    Type="String",
    AllowedPattern='[a-z-]+'
))
BUCKET = TEMPLATE.add_resource(bucket_build(Ref(BUCKET_NAME), UseEncryption=True))
BUCKET_SSM = TEMPLATE.add_resource(
    SSMParam(
        "SsmBucketName",
        Name='PipelineArtifactsBucket',
        Value=Ref(BUCKET),
        Type="String"
    )
)
OUTPUTS = output_with_export(
    BUCKET, True
)
TEMPLATE.add_output(OUTPUTS)

if ARGS.json:
    print(TEMPLATE.to_json())
else:
    print(TEMPLATE.to_yaml())
