# src/custom_constructs/iam_construct.py
from aws_cdk import aws_iam as iam
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class IamConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # 1. ECS Task Execution Role with all required policies
        self._task_execution_role = iam.Role(
            self,
            "EcsTaskExecutionRole",
            role_name=f"ecsTaskExecutionRole-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Allows ECS tasks to call AWS services on your behalf.",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchReadOnlyAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonKinesisFirehoseFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSQSFullAccess")
            ]
        )

        # 2. S3 Access Policy
        self._s3_access_policy = iam.ManagedPolicy(
            self,
            "OutlierAPIS3AccessPolicy",
            managed_policy_name=f"OutlierAPIS3AccessPolicy-{self.environment}-test",
            statements=[
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
            ]
        )

        # 3. Secrets Manager Policy
        self._secrets_policy = iam.ManagedPolicy(
            self,
            "OutlierAPISecretManagerReadPolicy",
            managed_policy_name=f"OutlierAPISecretManagerReadPolicy-{self.environment}-test",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["secretsmanager:GetSecretValue"],
                    resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:outlier-api-secrets*"]
                )
            ]
        )

        # 4. CodeDeploy Role
        self._codedeploy_role = iam.Role(
            self,
            "CodeDeployRole",
            role_name=f"AWSCodeDeployRoleForECS-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("codedeploy.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeDeployRoleForECS")
            ]
        )

        # 5. CodeBuild Role and Policy
        self._codebuild_role = iam.Role(
            self,
            "CodeBuildRole",
            role_name=f"codebuild-outlier-service-codebuild-{self.environment}-test-service-role",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com")
        )

        # CodeBuild Base Policy
        self._codebuild_policy = iam.Policy(
            self,
            "CodeBuildBasePolicy",
            policy_name=f"CodeBuildBasePolicy-outlier-service-codebuild-{self.environment}-test",
            statements=[
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
            ],
            roles=[self._codebuild_role]
        )

        # 6. Datadog Integration Policy
        self._datadog_policy = iam.Policy(
            self,
            "DatadogPolicy",
            policy_name=f"DatadogInfrastructureMetricsIntegrationPolicy-{self.environment}-test",
            statements=[
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
            ],
            roles=[self._task_execution_role]
        )

    # Property accessors
    @property
    def task_execution_role(self) -> iam.IRole:
        return self._task_execution_role

    @property
    def codedeploy_role(self) -> iam.IRole:
        return self._codedeploy_role

    @property
    def codebuild_role(self) -> iam.IRole:
        return self._codebuild_role