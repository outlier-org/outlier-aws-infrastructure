# src/stacks/base_stack.py
import aws_cdk as cdk
from constructs import Construct
from custom_constructs.network_construct import NetworkConstruct
from custom_constructs.storage_construct import StorageConstruct
from custom_constructs.iam_construct import IamConstruct
from custom_constructs.ecr_construct import EcrConstruct
from custom_constructs.alb_construct import AlbConstruct
from custom_constructs.ecs_construct import EcsConstruct
from custom_constructs.pipeline_construct import CodePipelineConstruct

class BaseStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstruct(self, "NetworkConstruct")

        # Storage resources (S3 buckets)
        storage = StorageConstruct(self, "StorageConstruct")

        # IAM resources
        iam = IamConstruct(self, "IamConstruct")

        # ECR repository - referenced by both ECS and CodePipeline
        ecr = EcrConstruct(self, "EcrConstruct")

        # Create ALB with target groups
        alb = AlbConstruct(
            self,
            "AlbConstruct",
            vpc=network.vpc,
            security_group=network.alb_security_group,
            subnets=network.vpc.public_subnets
        )

        # Create ECS resources - now using proper image from ECR
        ecs = EcsConstruct(
            self,
            "EcsConstruct",
            vpc=network.vpc,
            security_groups=[network.service_security_group],
            execution_role=iam.task_execution_role,
            task_role=iam.task_role,
            service_target_group=alb.service_tg_1,
            jobs_target_group=alb.jobs_tg_1,
            ecr_repository=ecr.ecr_repository
        )

        # Create Pipeline resources with blue-green config
        pipeline = CodePipelineConstruct(
            self,
            "PipelineConstruct",
            ecs_cluster=ecs.cluster,
            ecs_service=ecs.service,
            ecs_jobs_service=ecs.jobs_service,
            ecr_repository=ecr.ecr_repository,
            prod_listener=alb.production_listener,
            test_listener=alb.test_listener,
            service_target_groups=[
                alb.service_tg_1,
                alb.service_tg_2
            ],
            jobs_target_groups=[
                alb.jobs_tg_1,
                alb.jobs_tg_2
            ]
        )

        # Add output for ECR repository URI
        cdk.CfnOutput(
            self,
            "EcrRepositoryUri",
            value=ecr.ecr_repository.repository_uri,
            description="ECR Repository URI"
        )

        # Add output for ALB DNS name
        cdk.CfnOutput(
            self,
            "AlbDnsName",
            value=alb.load_balancer.load_balancer_dns_name,
            description="Application Load Balancer DNS Name"
        )