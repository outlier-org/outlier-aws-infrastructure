import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (aws_ec2 as ec2)

from custom_constructs.network_construct_new import NetworkConstruct
from custom_constructs.ecr_construct_new import EcrConstruct
from custom_constructs.load_balancer_construct_new import LoadBalancerConstruct
from custom_constructs.ecs_construct_new import EcsConstruct
from custom_constructs.pipeline_construct_new import PipelineConstruct


class EcsBlueGreenStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Configuration parameters
        vpc_id = "vpc-00059e30c80aa84f2"
        rds_sg_id = "sg-05fcdaf33c1d2a016"
        ecr_repo_name = "outlier-ecr-nightly"
        cert_arn = "arn:aws:acm:us-east-1:528757783796:certificate/71eac7f3-f4f4-4a6c-a32b-d6dad41f94e8"
        hosted_zone_id = "Z05574991AFW5NGZ1X8DH"
        zone_name = "nightly.savvasoutlier.com"

        # Network resources
        network = NetworkConstruct(
            self,
            "Network",
            vpc_id=vpc_id,
            rds_sg_id=rds_sg_id,
        )

        # ECR Repository
        ecr = EcrConstruct(
            self,
            "ECR",
            repository_name=ecr_repo_name
        )

        # Load Balancer and DNS
        load_balancer = LoadBalancerConstruct(
            self,
            "LoadBalancer",
            vpc=network.vpc,
            security_group=network.alb_security_group,
            cert_arn=cert_arn,
            hosted_zone_id=hosted_zone_id,
            zone_name=zone_name
        )

        # ECS Cluster, Service and Task Definition
        ecs = EcsConstruct(self, "ECS",
                           vpc=network.vpc,
                           security_group=network.service_security_group,
                           ecr_repository=ecr.repository,
                           blue_target_group=load_balancer.blue_target_group,
                           account=self.account,
                           region=self.region,
       )

        # CI/CD Pipeline
        pipeline = PipelineConstruct(self, "Pipeline",
                                     service=ecs.service,
                                     https_listener=load_balancer.https_listener,
                                     http_listener=load_balancer.http_listener,
                                     blue_target_group=load_balancer.blue_target_group,
                                     green_target_group=load_balancer.green_target_group,
                                     account=self.account,
                                     region=self.region,
                                     )
