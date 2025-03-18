import aws_cdk as cdk
from constructs import Construct
from aws_cdk import aws_ec2 as ec2

from custom_constructs.network_construct_new import NetworkConstructNew
from custom_constructs.ecr_construct_new import EcrConstructNew
from custom_constructs.alb_construct_new import AlbConstructNew
from custom_constructs.ecs_construct_new import EcsConstructNew
from custom_constructs.pipeline_construct_new import PipelineConstructNew
from custom_constructs.waf_construct import WafConstruct

class DevApplicationStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstructNew(
            self,
            "Network-Dev",  # resource-dev pattern
            suffix="dev"
        )

        # ECR Repository
        ecr = EcrConstructNew(
            self,
            "ECR-Dev",  # resource-dev pattern
            repository_name="outlier-ecr-dev"
        )

        # Load Balancer and DNS
        alb = AlbConstructNew(
            self,
            "LoadBalancer-Dev",  # resource-dev pattern
            vpc=network.vpc,
            security_group=network.alb_security_group,
            load_balancer_name="outlier-dev",
            subdomain="api.dev"
        )

        # Create and associate WAF
        waf = WafConstruct(
            self,
            "WAF-Dev",
            alb=alb.alb,
            suffix="dev"
        )

        # ECS Cluster, Service and Task Definition
        ecs = EcsConstructNew(
            self,
            "ECS-Dev",  # resource-dev pattern
            vpc=network.vpc,
            security_group=network.service_security_group,
            ecr_repository=ecr.repository,
            blue_target_group=alb.blue_target_group,
            desired_count=1,
            cluster_name="outlier-dev",
            container_name="Outlier-Service-Container-nightly-dev",
            log_group_name="/ecs/Outlier-Service-nightly-dev"
        )

        # CI/CD Pipeline
        pipeline = PipelineConstructNew(
            self,
            "Pipeline-Dev",
            service=ecs.service,
            https_listener=alb.https_listener,
            http_listener=alb.http_listener,
            blue_target_group=alb.blue_target_group,
            green_target_group=alb.green_target_group,
            application_name="outlier-dev",
            deployment_group_name="outlier-dev",
            pipeline_name="outlier-dev",
            source_branch="cdk-dev-application-changes",
            repository_uri=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/outlier-ecr-dev",
            service_name="outlier-service-dev",
            buildspec_filename="buildspec_nightly.yml",
            appspec_filename="appspec_nightly_dev.yaml",
            taskdef_filename="taskdef_nightly_dev.json",
            environment_value="DEV"  # Override the default value
        )

        # Outputs
        cdk.CfnOutput(self, "ALBDnsName-Dev", value=alb.alb.load_balancer_dns_name)