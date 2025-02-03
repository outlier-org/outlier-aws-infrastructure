# src/custom_constructs/demo_construct.py
from aws_cdk import aws_s3 as s3
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class DemoConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # Demo S3 Bucket
        self.demo_bucket = s3.Bucket(
            self,
            "DemoBucket",
            bucket_name=f"outlier-demo-bucket-{self.environment}-test",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.DESTROY  # For easy demo cleanup
        )

        # Add standard tags
        cdk.Tags.of(self.demo_bucket).add("bounded_context", "outlier")
        cdk.Tags.of(self.demo_bucket).add("env", self.environment)
        cdk.Tags.of(self.demo_bucket).add("demo", "true")

    @property
    def bucket(self) -> s3.IBucket:
        return self.demo_bucket