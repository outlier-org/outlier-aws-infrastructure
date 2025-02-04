# src/custom_constructs/ecs_construct.py
from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecr as ecr,
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
            ecr_repository: ecr.IRepository,
    ):
        super().__init__(scope, id)

        # Create ECS Cluster
        self._cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=f"outlier-service-cluster-{self.environment}-test",
            vpc=vpc,
            container_insights=True  # Enable container insights for better monitoring
        )

        # Enable Fargate capacity providers
        self._cluster.enable_fargate_capacity_providers()

        # Main Service Task Definition
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
            image=ecs.ContainerImage.from_ecr_repository(
                ecr_repository,
                tag="latest"  # Initial tag, will be updated by CodeDeploy
            ),
            cpu=3072,
            memory_limit_mib=6144,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=f"outlier-service-{self.environment}-test",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING
            ),
            health_check={
                "command": ["CMD-SHELL", "curl -f http://localhost:1337/health || exit 1"],
                "interval": Duration.seconds(30),
                "timeout": Duration.seconds(5),
                "retries": 3,
                "startPeriod": Duration.seconds(60)
            }
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
            family=f"outlier-job-task-{self.environment}-test",
            cpu=4096,
            memory_limit_mib=8192,
            execution_role=execution_role,
            task_role=task_role
        )

        jobs_container = jobs_task_def.add_container(
            "JobsContainer",
            container_name=f"outlier-job-container-{self.environment}-test",
            image=ecs.ContainerImage.from_ecr_repository(
                ecr_repository,
                tag="latest"  # Initial tag, will be updated by CodeDeploy
            ),
            cpu=3072,
            memory_limit_mib=6144,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=f"outlier-jobs-{self.environment}-test",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING
            ),
            health_check={
                "command": ["CMD-SHELL", "curl -f http://localhost:1337/health || exit 1"],
                "interval": Duration.seconds(30),
                "timeout": Duration.seconds(5),
                "retries": 3,
                "startPeriod": Duration.seconds(60)
            }
        )

        jobs_container.add_port_mappings(
            ecs.PortMapping(
                container_port=1337,
                protocol=ecs.Protocol.TCP
            )
        )

        # Create the main service with blue-green deployment configuration
        self._service = ecs.FargateService(
            self,
            "Service",
            service_name=f"outlier-service-ecs-{self.environment}-test",
            cluster=self._cluster,
            task_definition=service_task_def,
            desired_count=2,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
            security_groups=security_groups,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            assign_public_ip=False,
            health_check_grace_period=Duration.seconds(60),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            ),
            circuit_breaker=ecs.DeploymentCircuitBreaker(
                rollback=True
            ),
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE",
                    weight=1,
                    base=1  # Ensure at least one task runs on FARGATE
                ),
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT",
                    weight=3  # 75% of tasks will use SPOT if available
                )
            ]
        )

        # Create the jobs service with blue-green deployment configuration
        self._jobs_service = ecs.FargateService(
            self,
            "JobsService",
            service_name=f"outlier-job-service-ecs-{self.environment}-test",
            cluster=self._cluster,
            task_definition=jobs_task_def,
            desired_count=1,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
            security_groups=security_groups,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            assign_public_ip=False,
            health_check_grace_period=Duration.seconds(60),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            ),
            circuit_breaker=ecs.DeploymentCircuitBreaker(
                rollback=True
            ),
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE",
                    weight=1
                )
            ]
        )

        # Add autoscaling to main service
        scaling = self._service.auto_scale_task_count(
            max_capacity=4,
            min_capacity=2
        )

        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60)
        )

        # Add autoscaling to jobs service
        jobs_scaling = self._jobs_service.auto_scale_task_count(
            max_capacity=2,
            min_capacity=1
        )

        jobs_scaling.scale_on_cpu_utilization(
            "JobsCpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60)
        )

        # Attach load balancer target groups
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