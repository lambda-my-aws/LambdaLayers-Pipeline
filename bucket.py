"""
Generic Bucket build attempt
"""
from troposphere import (
    Sub
)
from troposphere.s3 import (
    Bucket,
    LifecycleConfiguration,
    LifecycleRule,
    VersioningConfiguration,
    AbortIncompleteMultipartUpload,
    BucketEncryption,
    SseKmsEncryptedObjects,
    SourceSelectionCriteria,
    ServerSideEncryptionRule,
    ServerSideEncryptionByDefault,
    ReplicationConfiguration,
    ReplicationConfigurationRules,
    ReplicationConfigurationRulesDestination,
    EncryptionConfiguration
)
from cloudformation.tags.s3 import (
    s3_default_tags
)

S3_ARN = 'arn:aws:s3:::'

def set_replication_rule(replica_bucket, **kwargs):
    """
    returns:
        Bucket replication rule
    """
    if isinstance(replica_bucket, str):
        if replica_bucket.startswith('arn:aws:s3:::'):
            replica_bucket_arn = replica_bucket
        else:
            replica_bucket_arn = f'{S3_ARN}{replica_bucket}'
    else:
        replica_bucket_arn = replica_bucket

    destination = ReplicationConfigurationRulesDestination(
        Bucket=replica_bucket_arn
    )
    print(replica_bucket_arn)
    if 'UseEncryptionReplication' in kwargs.keys() and kwargs['UseEncryptionReplication']:
        encryption_config = EncryptionConfiguration(
            ReplicaKmsKeyID=kwargs['EncryptionKeyId']
        )
        setattr(destination, 'EncryptionConfiguration', encryption_config)
    if 'ReplicateEncryptedObjects' in kwargs.items() and kwargs['ReplicateEncryptedObjects']:
        source_criteria = SourceSelectionCriteria(
            SseKmsEncryptedObjects=SseKmsEncryptedObjects(
                Status='Enabled'
            )
        )
    else:
        source_criteria = SourceSelectionCriteria(
            SseKmsEncryptedObjects=SseKmsEncryptedObjects(
                Status='Disabled'
            )
        )
    rule = ReplicationConfigurationRules(
        Prefix='',
        Status='Enabled',
        Destination=destination,
        SourceSelectionCriteria=source_criteria
    )
    return rule


def set_bucket_replication(**kwargs):
    """
    returns:
        bucket replication configuration
    """
    config = ReplicationConfiguration(
        Role=kwargs['ReplicationRole'],
        Rules=[
            set_replication_rule(
                kwargs['DestinationBucket'],
                **kwargs
            )
        ]
    )
    return config


def set_bucket_lifecycle():
    """
    returns:
        LifecycleConfiguration for S3Bucket
    """
    config = LifecycleConfiguration(
        Rules=[
            LifecycleRule(
                Status='Enabled',
                AbortIncompleteMultipartUpload=AbortIncompleteMultipartUpload(
                    DaysAfterInitiation=3
                )
            )
        ]
    )
    return config


def set_bucket_encryption():
    """
    returns:
        EncryptionConfiguration for S3Bucket
    """
    config = BucketEncryption(
        ServerSideEncryptionConfiguration=[
            ServerSideEncryptionRule(
                ServerSideEncryptionByDefault=ServerSideEncryptionByDefault(
                    SSEAlgorithm='aws:kms'
                )
            )
        ]
    )
    return config


def bucket_build(bucket_name, **kwargs):
    """
    returns:
        S3Bucket
    """
    bucket = Bucket(
        "S3Bucket",
        Tags=s3_default_tags(
            **{
                '10-technical:usage': 'PipelineArtifacts',
                '40-security:compliance': 'None',
                '30-automation:project': 'Pipelines'
            }
        ),
        BucketName=bucket_name,
    )
    if 'UseEncryption' in kwargs.keys() and kwargs['UseEncryption']:
        setattr(bucket, 'BucketEncryption', set_bucket_encryption())
    if 'UseLifecycle' in kwargs.keys() and kwargs['UseLifecycle']:
        setattr(
            bucket, 'LifecycleConfiguration', set_bucket_lifecycle()
        )
        if not hasattr(bucket, 'VersioningConfiguration'):
            setattr(
                bucket, 'VersioningConfiguration',
                VersioningConfiguration(
                    Status='Enabled'
                )
            )
    if 'UseReplication' in kwargs.keys() and kwargs['UseReplication']:
        setattr(
            bucket,
            'ReplicationConfiguration',
            set_bucket_replication(
                **kwargs
            )
        )
        if not hasattr(bucket, 'VersioningConfiguration'):
            setattr(
                bucket, 'VersioningConfiguration',
                VersioningConfiguration(
                    Status='Enabled'
                )
            )
    return bucket

if __name__ == '__main__':
    import json
    print(
        json.dumps(
            bucket_build(
                'test',
                UseEncryption=False,
                UseLifecycle=False,
                UseReplication=True,
                UseEncryptionReplication=False,
                ReplicationRole='arn:aws:iam:::role/toto',
                DestinationBucket='destination-finale',
                EncryptionKeyId=Sub('some-id-like-that')
            ).to_dict(),
            indent=2
        )
    )
