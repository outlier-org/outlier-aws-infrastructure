# src/stacks/base_stack.py
import aws_cdk as cdk
from constructs import Construct
from custom_constructs.network_construct import NetworkConstruct
# from custom_constructs.storage_construct import StorageConstruct
from custom_constructs.iam_construct import IamConstruct
from custom_constructs.alb_construct import AlbConstruct
from custom_constructs.database_construct import DatabaseConstruct
from custom_constructs.ecs_construct import EcsConstruct
from custom_constructs.waf_construct import WafConstruct

class BaseStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstruct(self, "NetworkConstruct")

        # Storage resources (S3 buckets)
        # storage = StorageConstruct(self, "StorageConstruct")

        # IAM resources
        iam = IamConstruct(self, "IamConstruct")

        # Create ALB with target groups
        alb = AlbConstruct(
            self,
            "AlbConstruct",
            vpc=network.vpc,
            security_group=network.alb_security_group
        )

        # Create WAF and attach it to the ALB
        waf = WafConstruct(
            self,
            "WafConstruct",
            alb=alb.alb  # We pass the actual ALB instance
        )

        # Add the database construct - using the existing RDS security group
        database = DatabaseConstruct(
            self,
            "DatabaseConstruct",
            vpc=network.vpc,
            security_group=network.rds_security_group
        )

        # Create ECS resources
        ecs = EcsConstruct(
            self,
            "EcsConstruct",
            vpc=network.vpc,
            security_groups=[network.service_security_group],
            service_target_group=alb.main_target_group,
            jobs_target_group=alb.jobs_target_group
        )
