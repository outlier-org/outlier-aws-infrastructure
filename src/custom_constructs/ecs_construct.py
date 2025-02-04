# src/custom_constructs/ecs_construct.py
from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    Duration
)
from constructs import Construct
from .base_construct import BaseConstruct

class EcsConstruct(BaseConstruct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            vpc: ec2.IVpc,
            security_groups: list[ec2.ISecurityGroup],
            execution_role: iam.IRole,
            task_role: iam.IRole,
            service_target_group: elbv2.IApplicationTargetGroup,
            jobs_target_group: elbv2.IApplicationTargetGroup,
    ):
        super().__init__(scope, id)

        # Create ECS Cluster
        self._cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=f"outlier-service-cluster-{self.environment}-test",
            vpc=vpc,
            container_insights=True
        )

        # Enable Fargate capacity providers
        self._cluster.enable_fargate_capacity_providers()

        # Main Service Task Definition - Basic setup only
        service_task_def = ecs.FargateTaskDefinition(
            self,
            "ServiceTaskDef",
            family=f"outlier-service-task-{self.environment}-test",
            cpu=4096,
            memory_limit_mib=8192,
            execution_role=execution_role,
            task_role=task_role
        )

        service_container = service_task_def.add_container(
            "ServiceContainer",
            container_name=f"outlier-service-container-{self.environment}-test",
            image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),  # Placeholder only
            cpu=3072,
            memory_limit_mib=6144,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=f"outlier-service-{self.environment}-test",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING
            )
        )

        service_container.add_port_mappings(
            ecs.PortMapping(
                container_port=1337,
                protocol=ecs.Protocol.TCP
            )
        )

        # Jobs Service Task Definition - Basic setup only
        jobs_task_def = ecs.FargateTaskDefinition(
            self,
            "JobsTaskDef",
            family=f"outlier-job-task-{self.environment}-test",
            cpu=4096,
            memory_limit_mib=8192,
            execution_role=execution_role,
            task_role=task_role
        )

        jobs_container = jobs_task_def.add_container(
            "JobsContainer",
            container_name=f"outlier-job-container-{self.environment}-test",
            image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),  # Placeholder only
            cpu=3072,
            memory_limit_mib=6144,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=f"outlier-jobs-{self.environment}-test",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING
            )
        )

        jobs_container.add_port_mappings(
            ecs.PortMapping(
                container_port=1337,
                protocol=ecs.Protocol.TCP
            )
        )

        # Create the main service - Basic configuration only
        self._service = ecs.FargateService(
            self,
            "Service",
            service_name=f"outlier-service-ecs-{self.environment}-test",
            cluster=self._cluster,
            task_definition=service_task_def,
            desired_count=2,
            security_groups=security_groups,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            assign_public_ip=False,
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            )
        )

        # Create the jobs service - Basic configuration only
        self._jobs_service = ecs.FargateService(
            self,
            "JobsService",
            service_name=f"outlier-job-service-ecs-{self.environment}-test",
            cluster=self._cluster,
            task_definition=jobs_task_def,
            desired_count=1,
            security_groups=security_groups,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            assign_public_ip=False,
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            )
        )

        # Attach initial target groups
        self._service.attach_to_application_target_group(service_target_group)
        self._jobs_service.attach_to_application_target_group(jobs_target_group)

    @property
    def cluster(self) -> ecs.ICluster:
        return self._cluster

    @property
    def service(self) -> ecs.IService:
        return self._service

    @property
    def jobs_service(self) -> ecs.IService:
        return self._jobs_service