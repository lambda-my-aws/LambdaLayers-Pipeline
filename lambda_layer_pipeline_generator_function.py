from troposphere import (
    Template,
    Parameter,
    Output,
    Ref,
    Join,
    GetAtt
)

from troposphere.awslambda import (
    Function,
    Code,
    Content
)
from troposphere.ssm import (
    Parameter as SSMParam
)

TEMPLATE = Template()
TEMPLATE.add_description("""Template to create the Lambda Function that generates the """
                    """CFN template for the Lambda Function that itself generates """
                    """the Lambda Layer templates for CodePipeline"""
)


lambda_layer_lambda_generator_role_arn = TEMPLATE.add_parameter(Parameter(
    "LambdaLayerLambdaGeneratorRole",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="LambdaLayersPipeline-LambdaRoleArn"

))

lambda_layer_troposphere_arn = TEMPLATE.add_parameter(Parameter(
    "LambdaLayerTroposphereArn",
    Type="AWS::SSM::Parameter::Value<String>",
    Default="LambdaLayers-troposphere-Arn"

))


platform_init_bucket = TEMPLATE.add_parameter(Parameter(
    "PlatformInitialSourceBucket",
    Type="String",
    AllowedPattern="[\\x20-\\x7E]*"
))


lambda_layer_generator_code_s3_key = TEMPLATE.add_parameter(Parameter(
    "LambdaLayerGeneratorCodeS3Key",
    Type="String",
    AllowedPattern="[\\x20-\\x7E]*"
))


lambda_function = TEMPLATE.add_resource(Function(
    "LambdaLayersTemplateGenerator",
    Code=Code(
        S3Bucket=Ref(platform_init_bucket),
        S3Key=Ref(lambda_layer_generator_code_s3_key)
    ),
    Handler='lambda_layer_version_pipeline_template_generator.lambda_handler',
    Role=Ref(lambda_layer_lambda_generator_role_arn),
    Runtime="python3.7",
    MemorySize="256",
    Timeout=5,
    Layers=[
        Ref(lambda_layer_troposphere_arn)
    ]
))

ssm_function_arn = TEMPLATE.add_resource(SSMParam(
    "SsmLambdaFunctionArn",
    Name='LambdaLayers-GeneratorFunction-Arn',
    Value=GetAtt(lambda_function, 'Arn'),
    Type="String"
))

ssm_function_name = TEMPLATE.add_resource(SSMParam(
    "SsmLambdaFunctionName",
    Name='LambdaLayers-GeneratorFunction-Name',
    Value=Ref(lambda_function),
    Type="String"
))

TEMPLATE.add_output([
    Output(
        "LambdaFunctionArn",
        Value=GetAtt(lambda_function, 'Arn'),
        Description="ARN of the Lambda Function"
    ),
    Output(
        "LambbdaFunctionName",
        Value=Ref(lambda_function),
        Description="Name of the Lambda Function"
    )
])


if __name__ == '__main__':
    import argparse
    import sys
    PARSER = argparse.ArgumentParser("Generate a template for a new Lambda Function")
    PARSER.add_argument(
        "--yaml", required=False, action='store_true', help="Render in YAML"
    )
    PARSER.add_argument(
        "--create-stack", action='store_true', help="Creates a new stack with the generated template"
    )
    PARSER.add_argument(
        "--s3-bucket", required=False,
        help="Name of the s3 bucket that contains the Layer code"
    )
    PARSER.add_argument(
        "--s3-key", required=False, help="Name of the s3 key that contains the Layer code"
    )
    ARGS = PARSER.parse_args()
    if ARGS.create_stack and not (ARGS.s3_bucket and ARGS.s3_key):
        print("Create stack requires the S3 bucket and S3 key paramters")
        sys.exit(1)
    if ARGS.yaml:
        print(TEMPLATE.to_yaml())
    else:
        print(TEMPLATE.to_json())

    if ARGS.create_stack:
        import boto3
        client = boto3.client('cloudformation')
        try:
            client.create_stack(
                StackName="LambdaLayers-TemplateGeneratorFunction-platform",
                TemplateBody=TEMPLATE.to_json(),
                Parameters=[
                    {
                        'ParameterKey': platform_init_bucket.title,
                        'ParameterValue': ARGS.s3_bucket
                    },
                    {
                        'ParameterKey': lambda_layer_generator_code_s3_key.title,
                        'ParameterValue': ARGS.s3_key
                    }
                ],
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

