from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ec2 as ec2
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class EcsConstruct(BaseConstruct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            vpc: ec2.IVpc,
            security_groups: list[ec2.ISecurityGroup]
    ):
        super().__init__(scope, id)

        # Create ECS Cluster
        self._cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=f"outlier-service-cluster-{self.environment}-test",
            vpc=vpc
        )

        # Import existing task definitions
        service_task_def = ecs.TaskDefinition.from_task_definition_arn(
            self,
            "ServiceTaskDef",
            "arn:aws:ecs:us-east-1:528757783796:task-definition/Outlier-Service-Task-nightly:16"
        )

        jobs_task_def = ecs.TaskDefinition.from_task_definition_arn(
            self,
            "JobsServiceTaskDef",
            "arn:aws:ecs:us-east-1:528757783796:task-definition/Outlier-job-task-nightly:16"
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
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            assign_public_ip=False,
            health_check_grace_period=cdk.Duration.seconds(60),
            deployment_controller=ecs.DeploymentController(type=ecs.DeploymentControllerType.CODE_DEPLOY)
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
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            assign_public_ip=False,
            health_check_grace_period=cdk.Duration.seconds(60),
            deployment_controller=ecs.DeploymentController(type=ecs.DeploymentControllerType.CODE_DEPLOY)
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
