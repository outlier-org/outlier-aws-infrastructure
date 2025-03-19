import aws_cdk as cdk
from constructs import Construct
from aws_cdk import aws_ec2 as ec2

from custom_constructs.network_construct import NetworkConstruct
from custom_constructs.ecr_construct import EcrConstruct
from custom_constructs.alb_construct import AlbConstruct
from custom_constructs.ecs_construct import EcsConstruct
from custom_constructs.pipeline_construct_new import PipelineConstructNew
from custom_constructs.waf_construct import WafConstruct

from src.custom_constructs.storage_construct import StorageConstruct


class DevApplicationStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        sub_environment = "dev"
        self.sub_environment = sub_environment

        # Tag all resources in the stack
        cdk.Tags.of(self).add("SubEnvironment", self.sub_environment)

        # Network resources
        network = NetworkConstruct(
            self,
            "Network",
            sub_environment=f"-{self.sub_environment}",
            create_endpoints=False,
            create_security_groups=True
        )

        # Storage resources (S3 buckets)
        storage = StorageConstruct(
            self,
            "StorageConstruct",
            sub_environment=f"-{self.sub_environment}",
        )


        # # Add the database construct - using the existing RDS security group
        # database = DatabaseConstruct(
        #     self,
        #     "DatabaseConstruct",
        #     vpc=network.vpc,
        #     security_group=network.rds_security_group,
        # )

        # ECR Repository
        ecr = EcrConstruct(
            self,
            "ECR",
            sub_environment=f"-{self.sub_environment}",
        )

        # Load Balancer and DNS
        alb = AlbConstruct(
            self,
            f"LoadBalancer-{self.sub_environment}",
            vpc=network.vpc,
            security_group=network.alb_security_group,
            load_balancer_name=f"outlier-{self.sub_environment}",
            subdomain=f"api-{self.sub_environment}",
        )

        # Create and associate WAF
        waf = WafConstruct(
            self,
            f"WAF-{self.sub_environment}",
            alb=alb.alb,
            sub_environment=f"-{self.sub_environment}",
        )

        # ECS Cluster, Service and Task Definition
        ecs = EcsConstruct(
            self,
            f"ECS-{self.sub_environment}",
            vpc=network.vpc,
            security_group=network.service_security_group,
            ecr_repository=ecr.repository,
            blue_target_group=alb.blue_target_group,
            desired_count=1,
            cluster_name=f"outlier-service-nightly-{self.sub_environment}",
            container_name=f"Outlier-Service-Container-nightly-{self.sub_environment}",
            log_group_name=f"/ecs/Outlier-Service-nightly-{self.sub_environment}",
        )

        # CI/CD Pipeline
        pipeline = PipelineConstructNew(
            self,
            f"Pipeline-{self.sub_environment}",
            service=ecs.service,
            https_listener=alb.https_listener,
            http_listener=alb.http_listener,
            blue_target_group=alb.blue_target_group,
            green_target_group=alb.green_target_group,
            application_name=f"outlier-nightly-{self.sub_environment}",
            deployment_group_name=f"outlier-{self.sub_environment}",
            pipeline_name=f"outlier-{self.sub_environment}",
            source_branch="cdk-dev-application-changes",
            repository_uri=ecr.repository.repository_uri,
            service_name=f"outlier-service-{self.sub_environment}",
            buildspec_filename="buildspec_nightly.yml",
            appspec_filename=f"appspec_nightly_{self.sub_environment}.yaml",
            taskdef_filename=f"taskdef_nightly_{self.sub_environment}.json",
            environment_value=self.sub_environment.upper(),
        )

        # Outputs
        # cdk.CfnOutput(self, "ALBDnsName-Dev", value=alb.alb.load_balancer_dns_name)
