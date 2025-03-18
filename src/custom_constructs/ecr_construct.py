# src/custom_constructs/ecr_construct_new.py
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import aws_ecr as ecr
from .base_construct import BaseConstruct


class EcrConstruct(BaseConstruct):
    def __init__(
        self, scope: Construct, id: str, repository_name: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self._repository = ecr.Repository(
            self,
            "EcrRepo",
            repository_name=repository_name,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep only the last 10 images",
                    max_image_count=10,  # Keep only the last 10 images
                    rule_priority=1,
                    tag_status=ecr.TagStatus.ANY,
                )
            ],
        )

    @property
    def repository(self) -> ecr.IRepository:
        return self._repository
