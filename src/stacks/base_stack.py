# src/stacks/base_stack.py
import aws_cdk as cdk
from constructs import Construct
from custom_constructs.network_construct import NetworkConstruct
from custom_constructs.storage_construct import StorageConstruct
from custom_constructs.iam_construct import IamConstruct
from custom_constructs.ecr_construct import EcrConstruct
from custom_constructs.alb_construct import AlbConstruct
from custom_constructs.ecs_construct import EcsConstruct
# from custom_constructs.pipeline_construct import CodePipelineConstruct
# from custom_constructs.database_construct import DatabaseConstruct

class BaseStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstruct(self, "NetworkConstruct")

        # Store security groups
        self.alb_sg = network.alb_security_group
        self.service_sg = network.service_security_group
        self.rds_sg = network.rds_security_group
        self.secrets_sg = network.secrets_manager_security_group

        # Storage resources (S3 buckets)
        storage = StorageConstruct(self, "StorageConstruct")

        # IAM resources
        iam = IamConstruct(self, "IamConstruct")

        # ECR repository
        ecr = EcrConstruct(self, "EcrConstruct")

        # Create ALB with target groups
        alb = AlbConstruct(
            self,
            "AlbConstruct",
            vpc=network.vpc,
            security_group=network.alb_security_group,
            subnets=network.vpc.public_subnets
        )

        # Create ECS resources
        ecs = EcsConstruct(
            self,
            "EcsConstruct",
            vpc=network.vpc,
            security_groups=[network.service_security_group],
            execution_role=iam.task_execution_role,
            task_role=iam.task_role,
            service_target_group=alb.service_tg_1,
            jobs_target_group=alb.jobs_tg_1
        )

        # Create Pipeline resources (commented until ready)
        # pipeline = CodePipelineConstruct(
        #     self,
        #     "PipelineConstruct",
        #     ecs_cluster=ecs.cluster,
        #     ecs_service=ecs.service,
        #     ecs_jobs_service=ecs.jobs_service,
        #     ecr_repository=ecr.repository,
        #     service_target_groups=[alb.service_tg_1, alb.service_tg_2],
        #     jobs_target_groups=[alb.jobs_tg_1, alb.jobs_tg_2]
        # )