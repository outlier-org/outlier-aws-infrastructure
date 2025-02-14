from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_secretsmanager as secretsmanager,
    Duration,
)
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
            service_target_group: elbv2.IApplicationTargetGroup,
            jobs_target_group: elbv2.IApplicationTargetGroup,
    ):
        super().__init__(scope, id)

        # Create ECS Cluster
        self._cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=f"outlier-service-cluster-{self.environment}-cdk",
            vpc=vpc,
            container_insights=True
        )

        # Create task definition
        service_task_def = ecs.FargateTaskDefinition(
            self,
            "ServiceTaskDef",
            family=f"Outlier-Service-Task-{self.environment}",
            cpu=4096,
            memory_limit_mib=8192,
            task_role=iam.Role.from_role_arn(
                self, "TaskRole",
                f"arn:aws:iam::528757783796:role/ecsTaskExecutionRole"
            ),
            execution_role=iam.Role.from_role_arn(
                self, "ExecutionRole",
                f"arn:aws:iam::528757783796:role/ecsTaskExecutionRole"
            )
        )

        # Create log group
        log_group = logs.LogGroup(
            self,
            "ServiceLogGroup",
            log_group_name=f"/ecs/Outlier-Service-{self.environment}",
        )

        # Add main container
        service_container = service_task_def.add_container(
            "ServiceContainer",
            container_name=f"Outlier-Service-Container-{self.environment}",
            image=ecs.ContainerImage.from_registry("528757783796.dkr.ecr.us-east-1.amazonaws.com/outlier-ecr:19"),
            cpu=3072,
            memory_limit_mib=6144,
            memory_reservation_mib=5120,
            essential=True,
            environment={
                "DATADOG_SERVICE": "outlier-service",
                "NODE_ENV": "production",
                "CLOUD_PROVIDER": "AWS"
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=log_group
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:1337/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3
            )
        )

        service_container.add_port_mappings(
            ecs.PortMapping(
                name="outlier-service-container-nightly-1337-tcp",
                container_port=1337,
                host_port=1337,
                protocol=ecs.Protocol.TCP
            )
        )

        # Add Datadog container
        datadog_container = service_task_def.add_container(
            "DatadogAgent",
            container_name="datadog-agent",
            image=ecs.ContainerImage.from_registry("datadog/agent:latest"),
            cpu=1024,
            memory_limit_mib=2048,
            memory_reservation_mib=1024,
            essential=True,
            environment={
                "DD_SERVICE": "outlier-service",
                "ECS_FARGATE": "true",
                "DD_APM_ENABLED": "true",
                "DD_ENV": self.environment
            },
            secrets={
                "DD_API_KEY": ecs.Secret.from_secrets_manager(
                    secretsmanager.Secret.from_secret_name_v2(
                        self, "DatadogSecret",
                        "DATADOG_API_KEY-UyF3IZ"
                    ),
                    field="VALUE"
                )
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=log_group
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "agent health"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(15)
            )
        )

        datadog_container.add_port_mappings(
            ecs.PortMapping(
                name="datadog-agent-8126-tcp",
                container_port=8126,
                host_port=8126,
                protocol=ecs.Protocol.TCP
            )
        )

        # Create the service
        self._service = ecs.FargateService(
            self,
            "Service",
            service_name=f"outlier-service-{self.environment}",
            cluster=self._cluster,
            task_definition=service_task_def,
            desired_count=2,
            security_groups=security_groups,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            assign_public_ip=False,
            health_check_grace_period=Duration.seconds(60)
        )

        # Attach target group
        self._service.attach_to_application_target_group(service_target_group)

    @property
    def cluster(self) -> ecs.ICluster:
        return self._cluster

    @property
    def service(self) -> ecs.FargateService:
        return self._service

# BASIC CONFIG THAT WORKS
# from aws_cdk import (
#     aws_ecs as ecs,
#     aws_ec2 as ec2,
#     aws_iam as iam,
#     aws_elasticloadbalancingv2 as elbv2,
#     Duration
# )
# from constructs import Construct
# from .base_construct import BaseConstruct
#
# class EcsConstruct(BaseConstruct):
#     def __init__(
#             self,
#             scope: Construct,
#             id: str,
#             vpc: ec2.IVpc,
#             security_groups: list[ec2.ISecurityGroup],
#             execution_role: iam.IRole,
#             task_role: iam.IRole,
#             service_target_group: elbv2.IApplicationTargetGroup,
#             jobs_target_group: elbv2.IApplicationTargetGroup,
#     ):
#         super().__init__(scope, id)
#
#         # Create ECS Cluster
#         self._cluster = ecs.Cluster(
#             self,
#             "EcsCluster",
#             cluster_name=f"outlier-service-cluster-{self.environment}-test-2",
#             vpc=vpc,
#             container_insights=True
#         )
#
#         # Main Service Task Definition
#         service_task_def = ecs.FargateTaskDefinition(
#             self,
#             "ServiceTaskDef",
#             family=f"outlier-service-task-{self.environment}",
#             cpu=256,
#             memory_limit_mib=512,
#             execution_role=execution_role,
#             task_role=task_role
#         )
#
#         service_container = service_task_def.add_container(
#             "ServiceContainer",
#             container_name=f"outlier-service-container-{self.environment}",
#             image=ecs.ContainerImage.from_registry("public.ecr.aws/docker/library/httpd:latest"),
#             memory_limit_mib=512,
#             logging=ecs.LogDrivers.aws_logs(
#                 stream_prefix=f"outlier-service-{self.environment}"
#             )
#         )
#
#         service_container.add_port_mappings(
#             ecs.PortMapping(
#                 container_port=80,
#                 protocol=ecs.Protocol.TCP
#             )
#         )
#
#         # Jobs Service Task Definition (identical except for names)
#         jobs_task_def = ecs.FargateTaskDefinition(
#             self,
#             "JobsTaskDef",
#             family=f"outlier-jobs-task-{self.environment}",
#             cpu=256,
#             memory_limit_mib=512,
#             execution_role=execution_role,
#             task_role=task_role
#         )
#
#         jobs_container = jobs_task_def.add_container(
#             "JobsContainer",
#             container_name=f"outlier-jobs-container-{self.environment}",
#             image=ecs.ContainerImage.from_registry("public.ecr.aws/docker/library/httpd:latest"),
#             memory_limit_mib=512,
#             logging=ecs.LogDrivers.aws_logs(
#                 stream_prefix=f"outlier-jobs-{self.environment}"
#             )
#         )
#
#         jobs_container.add_port_mappings(
#             ecs.PortMapping(
#                 container_port=80,
#                 protocol=ecs.Protocol.TCP
#             )
#         )
#
#         # Create the main service
#         self._service = ecs.FargateService(
#             self,
#             "Service",
#             service_name=f"outlier-service-{self.environment}",
#             cluster=self._cluster,
#             task_definition=service_task_def,
#             desired_count=2,
#             security_groups=security_groups,
#             vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
#             assign_public_ip=False,
#             health_check_grace_period=Duration.seconds(60)
#         )
#
#         # Create the jobs service
#         self._jobs_service = ecs.FargateService(
#             self,
#             "JobsService",
#             service_name=f"outlier-jobs-{self.environment}",
#             cluster=self._cluster,
#             task_definition=jobs_task_def,
#             desired_count=2,
#             security_groups=security_groups,
#             vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
#             assign_public_ip=False,
#             health_check_grace_period=Duration.seconds(60)
#         )
#
#         # Attach target groups
#         self._service.attach_to_application_target_group(service_target_group)
#         self._jobs_service.attach_to_application_target_group(jobs_target_group)
#
#     @property
#     def cluster(self) -> ecs.ICluster:
#         return self._cluster
#
#     @property
#     def service(self) -> ecs.IService:
#         return self._service
#
#     @property
#     def jobs_service(self) -> ecs.IService:
#         return self._jobs_service

# # src/custom_constructs/ecs_construct.py
# from aws_cdk import (
#     aws_ecs as ecs,
#     aws_ec2 as ec2,
#     aws_iam as iam,
#     aws_elasticloadbalancingv2 as elbv2,
#     Duration
# )
# from constructs import Construct
# from .base_construct import BaseConstruct
#
# class EcsConstruct(BaseConstruct):
#     def __init__(
#             self,
#             scope: Construct,
#             id: str,
#             vpc: ec2.IVpc,
#             security_groups: list[ec2.ISecurityGroup],
#             execution_role: iam.IRole,
#             task_role: iam.IRole,
#             service_target_group: elbv2.IApplicationTargetGroup,
#             jobs_target_group: elbv2.IApplicationTargetGroup,
#     ):
#         super().__init__(scope, id)
#
#         # Create ECS Cluster
#         self._cluster = ecs.Cluster(
#             self,
#             "EcsCluster",
#             cluster_name=f"outlier-service-cluster-{self.environment}-test",
#             vpc=vpc,
#             container_insights=True
#         )
#
#         # Enable Fargate capacity providers
#         self._cluster.enable_fargate_capacity_providers()
#
#         # Main Service Task Definition - Basic setup only
#         service_task_def = ecs.FargateTaskDefinition(
#             self,
#             "ServiceTaskDef",
#             family=f"outlier-service-task-{self.environment}-test",
#             cpu=4096,
#             memory_limit_mib=8192,
#             execution_role=execution_role,
#             task_role=task_role
#         )
#
#         service_container = service_task_def.add_container(
#             "ServiceContainer",
#             container_name=f"outlier-service-container-{self.environment}-test",
#             image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),  # Placeholder only
#             cpu=3072,
#             memory_limit_mib=6144,
#             logging=ecs.LogDrivers.aws_logs(
#                 stream_prefix=f"outlier-service-{self.environment}-test",
#                 mode=ecs.AwsLogDriverMode.NON_BLOCKING
#             )
#         )
#
#         service_container.add_port_mappings(
#             ecs.PortMapping(
#                 container_port=1337,
#                 protocol=ecs.Protocol.TCP
#             )
#         )
#
#         # Jobs Service Task Definition - Basic setup only
#         jobs_task_def = ecs.FargateTaskDefinition(
#             self,
#             "JobsTaskDef",
#             family=f"outlier-job-task-{self.environment}-test",
#             cpu=4096,
#             memory_limit_mib=8192,
#             execution_role=execution_role,
#             task_role=task_role
#         )
#
#         jobs_container = jobs_task_def.add_container(
#             "JobsContainer",
#             container_name=f"outlier-job-container-{self.environment}-test",
#             image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),  # Placeholder only
#             cpu=3072,
#             memory_limit_mib=6144,
#             logging=ecs.LogDrivers.aws_logs(
#                 stream_prefix=f"outlier-jobs-{self.environment}-test",
#                 mode=ecs.AwsLogDriverMode.NON_BLOCKING
#             )
#         )
#
#         jobs_container.add_port_mappings(
#             ecs.PortMapping(
#                 container_port=1337,
#                 protocol=ecs.Protocol.TCP
#             )
#         )
#
#         # Create the main service - Basic configuration only
#         self._service = ecs.FargateService(
#             self,
#             "Service",
#             service_name=f"outlier-service-ecs-{self.environment}-test",
#             cluster=self._cluster,
#             task_definition=service_task_def,
#             desired_count=2,
#             security_groups=security_groups,
#             vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
#             assign_public_ip=False,
#             deployment_controller=ecs.DeploymentController(
#                 type=ecs.DeploymentControllerType.CODE_DEPLOY
#             )
#         )
#
#         # Create the jobs service - Basic configuration only
#         self._jobs_service = ecs.FargateService(
#             self,
#             "JobsService",
#             service_name=f"outlier-job-service-ecs-{self.environment}-test",
#             cluster=self._cluster,
#             task_definition=jobs_task_def,
#             desired_count=1,
#             security_groups=security_groups,
#             vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
#             assign_public_ip=False,
#             deployment_controller=ecs.DeploymentController(
#                 type=ecs.DeploymentControllerType.CODE_DEPLOY
#             )
#         )
#
#         # Attach initial target groups
#         self._service.attach_to_application_target_group(service_target_group)
#         self._jobs_service.attach_to_application_target_group(jobs_target_group)
#
#     @property
#     def cluster(self) -> ecs.ICluster:
#         return self._cluster
#
#     @property
#     def service(self) -> ecs.IService:
#         return self._service
#
#     @property
#     def jobs_service(self) -> ecs.IService:
#         return self._jobs_service