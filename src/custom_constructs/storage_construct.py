# src/custom_constructs/storage_construct.py
from aws_cdk import aws_s3 as s3
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct


class StorageConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str, sub_environment: str = ""):
        super().__init__(scope, id)

        common_config = {
            "encryption": s3.BucketEncryption.S3_MANAGED,
            "bucket_key_enabled": True,
            "enforce_ssl": True,
            "block_public_access": s3.BlockPublicAccess.BLOCK_ALL,
            "object_ownership": s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            "removal_policy": cdk.RemovalPolicy.DESTROY,  # Critical for bucket deletion
            "auto_delete_objects": True  # Automatically empty bucket before deletion
        }

        # Drupal Files Bucket
        self.drupal_bucket = s3.Bucket(
            self,
            "DrupalBucket",
            bucket_name=f"outlier-alpha-drupal-files-{self.environment}{sub_environment}",
            **common_config
        )

        # Student Progress Bucket
        self.progress_bucket = s3.Bucket(
            self,
            "ProgressBucket",
            bucket_name=f"outlier-student-progress-{self.environment}{sub_environment}",
            **common_config
        )
