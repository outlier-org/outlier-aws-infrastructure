import aws_cdk as cdk
from constructs import Construct
from custom_constructs.network_construct import NetworkConstruct
from custom_constructs.storage_construct import StorageConstruct
from custom_constructs.iam_construct import IamConstruct
from custom_constructs.ecr_construct import EcrConstruct
from custom_constructs.alb_construct import AlbConstruct
# from custom_constructs.ecs_construct import EcsConstruct
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

        Create ALB with target groups
        alb = AlbConstruct(
            self,
            "AlbConstruct",
            vpc=network.vpc,
            security_group=network.alb_security_group,
            subnets=network.vpc.public_subnets
        )

        # Add ALB DNS output for easy verification
        cdk.CfnOutput(
            self,
            "LoadBalancerDNS",
            value=alb.load_balancer.load_balancer_dns_name,
            description="Load Balancer DNS Name"
        )
        #
        # # Create ECS resources
        # ecs = EcsConstruct(
        #     self,
        #     "EcsConstruct",
        #     vpc=network.vpc,
        #     security_groups=[network.service_security_group],
        #     service_target_group=alb.service_target_group,
        #     jobs_target_group=alb.jobs_target_group
        # )
        #
        # # Create Pipeline resources
        # pipeline = CodePipelineConstruct(
        #     self,
        #     "PipelineConstruct",
        #     ecs_cluster=ecs.ecs_cluster,
        #     ecs_service=ecs.ecs_service,
        #     ecs_jobs_service=ecs.ecs_jobs_service,
        #     ecr_repository=ecr.repository
        # )

        # Create outlier_nightly RDS database
        # database = DatabaseConstruct(
        #     self,
        #     "DatabaseConstruct",
        #     vpc=network.vpc,
        #     rds_security_groups=[network.rds_security_group]
        # )

        # Add outputs if needed for resource information
        # cdk.CfnOutput(
        #     self,
        #     "DrupalBucketName",
        #     value=storage.drupal_bucket.bucket_name,
        #     description="Drupal Files Bucket Name"
        # )
        #
        # cdk.CfnOutput(
        #     self,
        #     "ProgressBucketName",
        #     value=storage.progress_bucket.bucket_name,
        #     description="Student Progress Bucket Name"
        # )