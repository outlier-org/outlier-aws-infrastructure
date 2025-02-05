# src/custom_constructs/ecr_construct.py
from aws_cdk import aws_ecr as ecr
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class EcrConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        self.repository = ecr.Repository(
            self,
            "OutlierEcr",
            repository_name="outlier-ecr-test",
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Delete when imageCountMoreThan (10)",
                    max_image_count=10,
                    rule_priority=1,
                    tag_status=ecr.TagStatus.ANY
                )
            ],
        )

        # Add tags
        cdk.Tags.of(self.repository).add("bounded_context", "outlier")
        cdk.Tags.of(self.repository).add("env", self.environment)

    @property
    def ecr_repository(self) -> ecr.IRepository:
        return self.repository