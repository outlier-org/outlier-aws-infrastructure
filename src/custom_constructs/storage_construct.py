# src/custom_constructs/storage_construct.py
from aws_cdk import aws_s3 as s3
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class StorageConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # Drupal Files Bucket
        self.drupal_bucket = s3.Bucket(
            self,
            "DrupalBucket",
            bucket_name=f"outlier-alpha-drupal-files-{self.environment}-test",
            encryption=s3.BucketEncryption.S3_MANAGED,
            bucket_key_enabled=True,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
        )
        cdk.Tags.of(self.drupal_bucket).add(
            "savvas:security:s3:public-bucket:exempt",
            "false"
        )

        # Student Progress Bucket
        self.progress_bucket = s3.Bucket(
            self,
            "ProgressBucket",
            bucket_name=f"outlier-student-progress-{self.environment}-test",
            encryption=s3.BucketEncryption.S3_MANAGED,
            bucket_key_enabled=True,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
        )
        cdk.Tags.of(self.progress_bucket).add(
            "savvas:security:s3:public-bucket:exempt",
            "false"
        )

        # Demo Bucket
        self.progress_bucket = s3.Bucket(
            self,
            "ProgressBucket",
            bucket_name=f"demo-{self.environment}-test",
            encryption=s3.BucketEncryption.S3_MANAGED,
            bucket_key_enabled=True,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
        )
        cdk.Tags.of(self.progress_bucket).add(
            "savvas:security:s3:public-bucket:exempt",
            "false"
        )