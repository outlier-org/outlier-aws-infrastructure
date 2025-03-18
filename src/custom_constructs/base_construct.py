import os
from aws_cdk import Names
from typing import Optional

import aws_cdk as cdk
from constructs import Construct


class BaseConstruct(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Environment should default to nightly, per current .projenrc.py
        self.environment = os.environ.get("ENVIRONMENT", "nightly")
        self.account = cdk.Stack.of(self).account
        self.region = cdk.Stack.of(self).region

        # Add common tags all resources should have
        self.tags = {
            "Environment": self.environment,
            "ManagedBy": "AWS-CDK-2",
            "Project": "outlier-aws-infrastructure",
        }

        # Add environment-specific configuration
        self.is_production = self.environment == "production"

    def add_tags(self, resource: cdk.ITaggable) -> None:
        """Add standard tags to AWS resources"""
        for key, value in self.tags.items():
            cdk.Tags.of(resource).add(key, value)

    @property
    def resource_identifier(self):
        return f"{self.environment}-{Names.unique_id(self)}"
