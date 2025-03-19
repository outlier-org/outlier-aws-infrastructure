# src/stacks/base_stack.py
import aws_cdk as cdk
from constructs import Construct
from custom_constructs.network_construct import NetworkConstruct

# from custom_constructs.storage_construct import StorageConstruct
from custom_constructs.iam_construct import IamConstruct
from custom_constructs.database_construct import DatabaseConstruct


class BaseStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstruct(
            self,
            "NetworkConstruct",
            create_endpoints=True,
            create_security_groups=False
        )

        # Storage resources (S3 buckets)
        # storage = StorageConstruct(self, "StorageConstruct")

        # IAM resources
        iam = IamConstruct(self, "IamConstruct")

        # # Add the database construct - using the existing RDS security group
        # database = DatabaseConstruct(
        #     self,
        #     "DatabaseConstruct",
        #     vpc=network.vpc,
        #     security_group=network.rds_security_group,
        # )
