# src/custom_constructs/iam_construct.py
from aws_cdk import aws_iam as iam
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class IamConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # Task Execution Role - used by ECS agent to pull images, write logs, etc
        self._task_execution_role = iam.Role(
            self,
            "EcsTaskExecutionRole",
            role_name=f"ecsTaskExecutionRole-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchReadOnlyAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"),
            ]
        )

        # Task Role - used by the actual running containers
        self._task_role = iam.Role(
            self,
            "EcsTaskRole",
            role_name=f"ecsTaskRole-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )

        # Add S3 permissions to Task Role
        self._task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::outlier-student-progress-{self.environment}-test",
                    f"arn:aws:s3:::outlier-student-progress-{self.environment}-test/*"
                ]
            )
        )

        # Add Secrets Manager permissions to Task Role
        self._task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:outlier-api-secrets*",
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:DATADOG_API_KEY*"
                ]
            )
        )

        # CodeDeploy Role
        self._codedeploy_role = iam.Role(
            self,
            "CodeDeployRole",
            role_name=f"AWSCodeDeployRoleForECS-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("codedeploy.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeDeployRoleForECS")
            ]
        )

        # CodeBuild Role
        self._codebuild_role = iam.Role(
            self,
            "CodeBuildRole",
            role_name=f"codebuild-outlier-service-codebuild-{self.environment}-test-service-role",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com")
        )

        # Add permissions to CodeBuild Role
        self._codebuild_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:PutImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:PutObject",
                    "s3:GetBucketAcl",
                    "s3:GetBucketLocation"
                ],
                resources=["*"]
            )
        )

        # Add Datadog monitoring permissions to Task Role
        self._task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecs:ListTasks",
                    "ecs:DescribeTasks",
                    "ecs:DescribeClusters",
                    "ecs:DescribeServices",
                    "ecs:ListServices",
                    "cloudwatch:GetMetricData",
                    "cloudwatch:ListMetrics",
                    "cloudwatch:DescribeAlarms",
                    "elasticloadbalancing:DescribeLoadBalancers",
                    "elasticloadbalancing:DescribeTargetGroups",
                    "elasticloadbalancing:DescribeTargetHealth",
                    "elasticloadbalancing:DescribeListeners",
                    "elasticloadbalancing:DescribeRules",
                    "elasticloadbalancing:DescribeTags",
                    "tag:GetResources",
                    "tag:GetTagKeys"
                ],
                resources=["*"]
            )
        )

    @property
    def task_execution_role(self) -> iam.IRole:
        return self._task_execution_role

    @property
    def task_role(self) -> iam.IRole:
        return self._task_role

    @property
    def codedeploy_role(self) -> iam.IRole:
        return self._codedeploy_role

    @property
    def codebuild_role(self) -> iam.IRole:
        return self._codebuild_role