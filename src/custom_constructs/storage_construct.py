from aws_cdk import aws_s3 as s3
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

"""
Storage Construct that provisions and manages S3 buckets for application data.
Implements standardized security and lifecycle configurations for all buckets.
"""


class StorageConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str, sub_environment: str = ""):
        super().__init__(scope, id)

        # Define common S3 bucket configuration
        common_config = {
            "encryption": s3.BucketEncryption.S3_MANAGED,
            "bucket_key_enabled": True,
            "enforce_ssl": True,
            "block_public_access": s3.BlockPublicAccess.BLOCK_ALL,
            "object_ownership": s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            "removal_policy": cdk.RemovalPolicy.DESTROY,  # Critical for bucket deletion
            "auto_delete_objects": True,  # Automatically empty bucket before deletion
        }

        # Create Drupal files storage bucket
        self.drupal_bucket = s3.Bucket(
            self,
            "DrupalBucket",
            bucket_name=f"outlier-alpha-drupal-files-{self.environment}{sub_environment}",
            **common_config,
        )

        # Create student progress storage bucket
        self.progress_bucket = s3.Bucket(
            self,
            "ProgressBucket",
            bucket_name=f"outlier-student-progress-{self.environment}{sub_environment}",
            **common_config,
        )
