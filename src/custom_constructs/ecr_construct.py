from aws_cdk import aws_ecr as ecr
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

from aws_cdk import aws_ecr as ecr

repository = ecr.Repository(
    self,
    "OutlierEcr",
    repository_name="outlier-ecr",
    lifecycle_rules=[
        ecr.LifecycleRule(
            description="Delete when imageCountMoreThan (10)",
            max_image_count=10,
            rule_priority=1,
            tag_status=ecr.TagStatus.ANY
        )
    ],
    removal_policy=cdk.RemovalPolicy.RETAIN
)

# Add tags
cdk.Tags.of(repository).add("bounded_context", "outlier")
cdk.Tags.of(repository).add("env", self.environment)