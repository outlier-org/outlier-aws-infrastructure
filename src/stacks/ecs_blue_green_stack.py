import aws_cdk as cdk
from constructs import Construct
from aws_cdk import aws_ec2 as ec2

from src.custom_constructs.network_construct_new import NetworkConstructNew
from src.custom_constructs.ecr_construct_new import EcrConstructNew
from src.custom_constructs.alb_construct_new import AlbConstructNew
from src.custom_constructs.ecs_construct_new import EcsConstructNew
from src.custom_constructs.pipeline_construct_new import PipelineConstructNew


class EcsBlueGreenStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstructNew(self, "Network")

        # ECR Repository
        ecr = EcrConstructNew(self, "ECR")

        # Load Balancer and DNS
        alb = AlbConstructNew(self, "LoadBalancer",
                              vpc=network.vpc,
                              security_group=network.alb_security_group)

        # ECS Cluster, Service and Task Definition
        ecs = EcsConstructNew(self, "ECS",
                              vpc=network.vpc,
                              security_group=network.service_security_group,
                              ecr_repository=ecr.repository,
                              blue_target_group=alb.blue_target_group)

        # CI/CD Pipeline
        pipeline = PipelineConstructNew(self, "Pipeline",
                                        service=ecs.service,
                                        https_listener=alb.https_listener,
                                        http_listener=alb.http_listener,
                                        blue_target_group=alb.blue_target_group,
                                        green_target_group=alb.green_target_group)

        # Outputs
        cdk.CfnOutput(self, "ALBDnsName", value=alb.alb.load_balancer_dns_name)