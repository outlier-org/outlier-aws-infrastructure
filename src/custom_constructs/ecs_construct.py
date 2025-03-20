# src/custom_constructs/ecs_construct_new.py
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
)
from .base_construct import BaseConstruct

"""
ECS Construct that creates and manages ECS resources including clusters, tasks, and services.
Implements blue-green deployment configuration for containerized applications.
"""


class EcsConstruct(BaseConstruct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.IVpc,
        security_group: ec2.ISecurityGroup,
        ecr_repository: ecr.IRepository,
        blue_target_group: elbv2.IApplicationTargetGroup,
        cluster_name: str = "outlier-blue-green",
        desired_count: int = 2,
        container_name: str = "Outlier-Service-Container-nightly",
        log_group_name: str = "/ecs/Outlier-Service-nightly",
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Initialize configuration parameters
        self.cluster_name = cluster_name
        self.desired_count = desired_count
        self.container_name = container_name
        self.log_group_name = log_group_name

        # Configure CloudWatch log group for ECS containers
        ecs_logs = logs.LogGroup(
            self,
            "EcsLogGroup",
            log_group_name=self.log_group_name,
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # Create ECS cluster within specified VPC
        self._cluster = ecs.Cluster(
            self, "Cluster", vpc=vpc, cluster_name=self.cluster_name
        )

        # Import existing task execution role
        task_execution_role = iam.Role.from_role_arn(
            self,
            "TaskExecutionRole",
            f"arn:aws:iam::{self.account}:role/ecsTaskExecutionRole",
        )

        # Configure permissions for ECR and Secrets Manager access
        task_execution_role.attach_inline_policy(
            iam.Policy(
                self,
                "TaskExecutionRolePolicy",
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "secretsmanager:GetSecretValue",
                            "ecr:GetAuthorizationToken",
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchGetImage",
                        ],
                        resources=["*"],
                    )
                ],
            )
        )

        # Define Fargate task with resource allocations
        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            execution_role=task_execution_role,
            task_role=task_execution_role,
            cpu=2048,  # 2 vCPU
            memory_limit_mib=4096,  # 4GB
        )

        # Configure container with image and port mapping
        app_container = task_definition.add_container(
            self.container_name,
            image=ecs.ContainerImage.from_ecr_repository(ecr_repository, tag="latest"),
        )
        app_container.add_port_mappings(ecs.PortMapping(container_port=1337))

        # Deploy Fargate service with blue-green deployment configuration
        self._service = ecs.FargateService(
            self,
            "Service",
            cluster=self._cluster,
            task_definition=task_definition,
            desired_count=self.desired_count,
            security_groups=[security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            ),
        )

        # Connect service to load balancer target group
        self._service.attach_to_application_target_group(blue_target_group)

    @property
    def cluster(self) -> ecs.ICluster:
        return self._cluster

    @property
    def service(self) -> ecs.FargateService:
        return self._service
