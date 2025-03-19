import aws_cdk as cdk
from constructs import Construct
from aws_cdk import aws_ec2 as ec2

from custom_constructs.network_construct import NetworkConstruct
from custom_constructs.ecr_construct import EcrConstruct
from custom_constructs.alb_construct import AlbConstruct
from custom_constructs.ecs_construct import EcsConstruct
from custom_constructs.pipeline_construct_old import PipelineConstructOld
from custom_constructs.waf_construct import WafConstruct
from custom_constructs.storage_construct import StorageConstruct
from custom_constructs.database_construct import DatabaseConstruct


class NightlyApplicationStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstruct(
            self, "Network", create_endpoints=False, create_security_groups=True
        )

        # Storage resources (S3 buckets)
        storage = StorageConstruct(self, "StorageConstruct")

        # # Add the database construct - using the existing RDS security group
        database = DatabaseConstruct(
            self,
            "DatabaseConstruct",
            vpc=network.vpc,
            security_group=network.rds_security_group,
        )

        # ECR Repository
        ecr = EcrConstruct(
            self,
            "ECR",
        )

        # Load Balancer and DNS
        alb = AlbConstruct(
            self,
            "LoadBalancer",
            vpc=network.vpc,
            security_group=network.alb_security_group,
            load_balancer_name="outlier-nightly",
            subdomain="api",
        )

        # Create and associate WAF
        waf = WafConstruct(
            self,
            "WAF",
            alb=alb.alb,
        )

        # ECS Cluster, Service and Task Definition
        ecs = EcsConstruct(
            self,
            "ECS",
            vpc=network.vpc,
            security_group=network.service_security_group,
            ecr_repository=ecr.repository,
            blue_target_group=alb.blue_target_group,
            desired_count=2,
            cluster_name="outlier-service-nightly",
            container_name="Outlier-Service-Container-nightly",
            log_group_name="/ecs/Outlier-Service-nightly",
        )

        # CI/CD Pipeline
        pipeline = PipelineConstructOld(
            self,
            "Pipeline",
            service=ecs.service,
            https_listener=alb.https_listener,
            http_listener=alb.http_listener,
            blue_target_group=alb.blue_target_group,
            green_target_group=alb.green_target_group,
            application_name="outlier-nightly",
            deployment_group_name="outlier",
            pipeline_name="outlier-nightly",
            source_branch="staging",
            repository_uri=ecr.repository.repository_uri,
            service_name="outlier-service",
            buildspec_filename="buildspec_nightly.yml",
            appspec_filename="appspec_nightly.yaml",
            taskdef_filename="taskdef_nightly.json",
            environment_value="NIGHTLY",
        )

        # Outputs
        # cdk.CfnOutput(self, "ALBDnsName-Dev", value=alb.alb.load_balancer_dns_name)
