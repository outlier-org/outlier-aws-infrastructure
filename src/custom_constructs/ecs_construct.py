# src/custom_constructs/ecs_construct.py
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
import aws_cdk as cdk
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
            jobs_target_group: elbv2.IApplicationTargetGroup
        ):
        super().__init__(scope, id)

        # Store the target groups
        self.service_target_group = service_target_group
        self.jobs_target_group = jobs_target_group

        # Create ECS Cluster
        self._cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=f"outlier-service-cluster-{self.environment}-test",
            vpc=vpc
        )

        # Add capacity providers
        self._cluster.add_capacity_provider("FARGATE")
        self._cluster.add_capacity_provider("FARGATE_SPOT")

        # Main Service Task Definition
        service_task_def = ecs.FargateTaskDefinition(
            self,
            "ServiceTaskDef",
            family=f"Outlier-Service-Task-{self.environment}-test",
            cpu=4096,
            memory_limit_mib=8192,
            execution_role=execution_role,
            task_role=task_role
        )

        service_container = service_task_def.add_container(
            "ServiceContainer",
            container_name=f"Outlier-Service-Container-{self.environment}-test",
            image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),  # Placeholder
            cpu=3072,
            memory_limit_mib=6144,
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_group=f"/ecs/Outlier-Service-{self.environment}-test"
            )
        )

        service_container.add_port_mappings(
            ecs.PortMapping(
                container_port=1337,
                protocol=ecs.Protocol.TCP
            )
        )

        # Jobs Service Task Definition
        jobs_task_def = ecs.FargateTaskDefinition(
            self,
            "JobsTaskDef",
            family=f"Outlier-job-task-{self.environment}-test",
            cpu=4096,
            memory_limit_mib=8192,
            execution_role=execution_role,
            task_role=task_role
        )

        jobs_container = jobs_task_def.add_container(
            "JobsContainer",
            container_name=f"Outlier-Job-Container-{self.environment}-test",
            image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),  # Placeholder
            cpu=3072,
            memory_limit_mib=6144,
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_group=f"/ecs/Outlier-job-{self.environment}-test"
            )
        )

        jobs_container.add_port_mappings(
            ecs.PortMapping(
                container_port=1337,
                protocol=ecs.Protocol.TCP
            )
        )

        # Main Service
        self._service = ecs.FargateService(
            self,
            "Service",
            service_name=f"outlier-service-ecs-{self.environment}-test",
            cluster=self._cluster,
            task_definition=service_task_def,
            desired_count=2,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
            security_groups=security_groups,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            assign_public_ip=False,
            health_check_grace_period=cdk.Duration.seconds(0),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            )
        )

        # Jobs Service
        self._jobs_service = ecs.FargateService(
            self,
            "JobsService",
            service_name=f"outlier-job-service-ecs-{self.environment}-test",
            cluster=self._cluster,
            task_definition=jobs_task_def,
            desired_count=1,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
            security_groups=security_groups,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            assign_public_ip=False,
            health_check_grace_period=cdk.Duration.seconds(0),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            )
        )

        # Attach load balancer target groups to main service
        self._service.attach_to_application_target_group(
            target_group=self.service_target_group
        )

        # Attach load balancer target groups to jobs service
        self._jobs_service.attach_to_application_target_group(
            target_group=self.jobs_target_group
        )

    @property
    def cluster(self) -> ecs.ICluster:
        return self._cluster

    @property
    def service(self) -> ecs.IService:
        return self._service

    @property
    def jobs_service(self) -> ecs.IService:
        return self._jobs_service