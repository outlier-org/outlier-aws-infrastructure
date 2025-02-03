# src/custom_constructs/iam_construct.py
from aws_cdk import aws_iam as iam
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class IamConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # ECS Task Execution Role
        self.execution_role = iam.Role(
            self,
            "EcsTaskExecutionRole",
            role_name=f"ecsTaskExecutionRole-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # Add Secrets Manager access for Datadog API key
        self.execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:DATADOG_API_KEY*"
                ]
            )
        )

        # ECS Task Role
        self.task_role = iam.Role(
            self,
            "EcsTaskRole",
            role_name=f"ecsTaskRole-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )

        # Add required permissions for task role
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:*",  # For the S3 buckets we created
                    "secretsmanager:GetSecretValue"  # For secrets access
                ],
                resources=["*"]  # We can scope this down if needed
            )
        )

    @property
    def ecs_execution_role(self) -> iam.IRole:
        return self.execution_role

    @property
    def ecs_task_role(self) -> iam.IRole:
        return self.task_role