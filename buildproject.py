from troposphere import (
    Template,
    Parameter,
    Output,
    Tags
)
from troposphere import (
    ImportValue,
    FindInMap,
    GetAtt,
    Select,
    Split,
    Ref,
    Sub
)
from troposphere import (
    Condition,
    Equals,
    Not,
    If
)
from troposphere.codebuild import (
    Environment,
    Source,
    Project,
    Artifacts
)
from troposphere.iam import (
    Role,
    Policy
)
from common import (
    ARTIFACTS_S3_BUCKET,
    TEAM_LANGUAGES,
    OU_NAME,
    COMPANY_TAG
)
from cloudformation.outputs import (
    output_with_export,
    output_no_export
)
from cloudformation.tags.s3 import s3_default_tags
from cloudformation.roles import role_trust_policy
from cloudformation.tags.codebuild import codebuild_default_tags
from codebuild.runtime import generate_runtime_mapping_and_parameters

PIPELINE_BUCKET_STACK = Parameter(
    'PipelineBucketStack',
    Type="String",
    Default="bucket-pipeline-artifacts"
)


def set_role_type(role):
    """
    returns:
        role as it is needed for the Lambda function to work
    """
    if isinstance(role, str):
        if role.startswith('arn:aws:iam::'):
            role_arn = role
        else:
            role_arn = Sub('arn:aws:iam::${AWS::AccountId}:role/{role}')
    elif isinstance(role, Role):
        role_arn = GetAtt(role, 'Arn')
    elif isinstance(role, (GetAtt, Sub, Ref)):
        role_arn = role
    else:
        raise TypeError('role expected to be of type', str, Role, Sub, GetAtt, Ref)
    return role_arn


def role_build():
    """
    returns:
        iam.Role
    """
    role = Role(
        "CodeBuildRole",
        Path='/cicd/codebuild/',
        AssumeRolePolicyDocument=role_trust_policy('codebuild'),
        ManagedPolicyArns=[
            'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        ],
        Policies=[
            Policy(
                PolicyName="S3Access",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            'Effect': 'Allow',
                            'Resource': [
                                Sub(
                                    '${BucketArn}/*',
                                    BucketArn=ImportValue(
                                        Sub(f'${{{PIPELINE_BUCKET_STACK.title}}}-S3Bucket-Arn')
                                    )
                                )
                            ],
                            'Action': [
                                's3:PutObject',
                                's3:PutObjectVersion',
                                's3:GetObject',
                                's3:GetObjectVersion'
                            ]
                        }
                    ]
                }
            )
        ]
    )
    return role


def get_build_project(
        project_role,
        runtime_language,
        runtime_version,
        **tags):
    """
    """
    project = Project(
        "BuildProject",
        Source=Source(Type='CODEPIPELINE'),
        Artifacts=Artifacts(
            Type='CODEPIPELINE',
            Packaging="ZIP",
            NamespaceType="NONE"
        ),
        Environment=Environment(
        ComputeType='BUILD_GENERAL1_SMALL',
            Image=FindInMap(
                'Languages',
                Ref(runtime_language),
                Ref(runtime_version)
            ),
            Type='LINUX_CONTAINER',
            EnvironmentVariables=[]
        ),
        ServiceRole=set_role_type(project_role),
        Tags=codebuild_default_tags(
            **tags
        )
    )
    return project


def template_build():
    """
    """
    template = Template()
    mappings_params = generate_runtime_mapping_and_parameters(
        TEAM_LANGUAGES
    )
    if not mappings_params[0]:
        exit(1)
    runtime_language = Parameter(
        "BuildRuntimeLanguage",
        Type="String",
        AllowedValues=mappings_params[2]
    )
    runtime_versions = Parameter(
        "BuildRuntimeVersion",
        Type="String",
        AllowedValues=mappings_params[3]
    )
    template.add_parameter(runtime_language)
    template.add_parameter(runtime_versions)
    template.add_mapping('Languages', mappings_params[1])
    role = role_build()
    project = get_build_project(
        set_role_type(role),
        runtime_language.title,
        runtime_versions.title,
        **{
            '10-technical:team': 'PlatformEngineering',
            '10-technical:runtime_language' : Ref(runtime_language),
            '10-technical:runtime_version' : Ref(runtime_versions)
        }
    )
    template.add_parameter(PIPELINE_BUCKET_STACK)
    template.add_resource(role)
    template.add_resource(project)
    template.add_output(
        output_with_export(
            project, True,
            **{
                'RuntimeLanguage': runtime_language,
                'RuntimeVersions': runtime_versions
            }))
    return template


if __name__ == '__main__':
    TEMPLATE = template_build()
    print(TEMPLATE.to_yaml())
