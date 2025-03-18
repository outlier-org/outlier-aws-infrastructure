import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2
)


class EcsConstruct(Construct):
    def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc,
                 security_group: ec2.ISecurityGroup, ecr_repository: ecr.IRepository,
                 blue_target_group: elbv2.IApplicationTargetGroup,
                 account: str, region: str, environment: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ECS Log Group
        ecs_logs = logs.LogGroup(
            self,
            "EcsLogGroup",
            log_group_name="/ecs/Outlier-Service-nightly",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        # ECS Cluster
        self.cluster = ecs.Cluster(
            self, "BlueGreenCluster",
            vpc=vpc,
            cluster_name="outlier-blue-green"
        )

        # Task Execution Role
        task_execution_role = iam.Role.from_role_arn(
            self, "TaskExecutionRole",
            f"arn:aws:iam::{account}:role/ecsTaskExecutionRole"
        )

        # Attach an inline policy
        task_execution_role.attach_inline_policy(
            iam.Policy(
                self, "TaskExecutionRolePolicy",
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "secretsmanager:GetSecretValue",
                            "ecr:GetAuthorizationToken",
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchGetImage"
                        ],
                        resources=["*"]
                    )
                ]
            )
        )

        # Task definition
        task_definition = ecs.FargateTaskDefinition(
            self, "BlueGreenTaskDef",
            execution_role=task_execution_role,
            task_role=task_execution_role,
            cpu=2048,  # 2 vCPU
            memory_limit_mib=4096  # 4GB
        )

        # Container configuration
        app_container = task_definition.add_container(
            "Outlier-Service-Container-nightly",
            image=ecs.ContainerImage.from_ecr_repository(
                ecr_repository,
                tag="latest"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=ecs_logs
            )
        )

        app_container.add_port_mappings(
            ecs.PortMapping(container_port=1337)
        )

        # Fargate Service
        self.service = ecs.FargateService(
            self, "BlueGreenService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=2,
            security_groups=[security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            )
        )

        # Attach the service to the ALB Target Group
        self.service.attach_to_application_target_group(blue_target_group)