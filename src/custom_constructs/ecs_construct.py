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
            vpc=vpc
        )

        self._cluster.enable_fargate_capacity_providers()

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

        # Using nginx as a test image that will respond to health checks
        service_container = service_task_def.add_container(
            "ServiceContainer",
            container_name=f"Outlier-Service-Container-{self.environment}-test",
            image=ecs.ContainerImage.from_registry("nginx:latest"),
            cpu=3072,
            memory_limit_mib=6144,
            port_mappings=[
                ecs.PortMapping(
                    container_port=80,  # Changed to 80 for nginx
                    protocol=ecs.Protocol.TCP
                )
            ],
            health_check={
                "command": ["CMD-SHELL", "curl -f http://localhost:80/ || exit 1"],
                "interval": Duration.seconds(30),
                "timeout": Duration.seconds(5),
                "retries": 3,
                "start_period": Duration.seconds(60)
            }
        )

        # Jobs Service Task Definition (similar changes)
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
            image=ecs.ContainerImage.from_registry("nginx:latest"),
            cpu=3072,
            memory_limit_mib=6144,
            port_mappings=[
                ecs.PortMapping(
                    container_port=80,
                    protocol=ecs.Protocol.TCP
                )
            ],
            health_check={
                "command": ["CMD-SHELL", "curl -f http://localhost:80/ || exit 1"],
                "interval": Duration.seconds(30),
                "timeout": Duration.seconds(5),
                "retries": 3,
                "start_period": Duration.seconds(60)
            }
        )

        # Create the main service without CodeDeploy initially
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
            health_check_grace_period=Duration.seconds(60),  # Increased from 0
            # Removed CODE_DEPLOY controller for initial deployment
        )

        # Create the jobs service
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
            health_check_grace_period=Duration.seconds(60),  # Increased from 0
            # Removed CODE_DEPLOY controller for initial deployment
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