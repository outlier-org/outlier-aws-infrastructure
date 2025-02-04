
        iam104a16f = iam.CfnManagedPolicy(
            self,
            "iam104a16f",
            managed_policy_name="CodeBuildBasePolicy-outlier-service-codebuild-nightly-us-east-1",
            path="/service-role/",
            policy_document='''
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Resource": [
                "arn:aws:logs:us-east-1:528757783796:log-group:/aws/codebuild/outlier-service-codebuild-nightly",
                "arn:aws:logs:us-east-1:528757783796:log-group:/aws/codebuild/outlier-service-codebuild-nightly:*"
            ],
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ]
        },
        {
            "Effect": "Allow",
            "Resource": [
                "arn:aws:s3:::codepipeline-us-east-1-*"
            ],
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:GetBucketAcl",
                "s3:GetBucketLocation"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "codebuild:CreateReportGroup",
                "codebuild:CreateReport",
                "codebuild:UpdateReport",
                "codebuild:BatchPutTestCases",
                "codebuild:BatchPutCodeCoverages"
            ],
            "Resource": [
                "arn:aws:codebuild:us-east-1:528757783796:report-group/outlier-service-codebuild-nightly-*"
            ]
        }
    ]
}
'''
        )

        iam92de94c = iam.CfnManagedPolicy(
            self,
            "iam92de94c",
            managed_policy_name="OutlierAPIS3AccessPolicy",
            path="/",
            policy_document='''
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Statement1",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::outlier-student-progress-nightly",
                "arn:aws:s3:::outlier-student-progress-nightly/*"
            ]
        }
    ]
}
'''
        )

        iam4349a15 = iam.CfnManagedPolicy(
            self,
            "iam4349a15",
            managed_policy_name="OutlierAPISecretManagerReadPolicy",
            path="/",
            policy_document='''
{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": [
                    "arn:aws:secretsmanager:us-east-1:528757783796:secret:outlier-api-secrets"
                ]
            }
        ]
    }
'''
        )


        iam47a21a0 = iam.CfnRole(
            self,
            "iam47a21a0",
            path="/",
            role_name="ecsTaskExecutionRole",
            assume_role_policy_document="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"\",\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"ecs-tasks.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}",
            max_session_duration=3600,
            managed_policy_arns=[
                iam4349a15.ref,
                iam92de94c.ref,
                "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
                "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess",
                "arn:aws:iam::aws:policy/AmazonKinesisFirehoseFullAccess",
                "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
                "arn:aws:iam::aws:policy/AmazonSQSFullAccess"
            ],
            description="Allows ECS tasks to call AWS services on your behalf."
        )

        iama49ec02 = iam.CfnPolicy(
            self,
            "iama49ec02",
            policy_document='''
{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
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
                "Resource": "*"
            }
        ]
    }
''',
            roles=[
                iam47a21a0.ref
            ],
            policy_name="DatadogInfrastructureMetricsIntegrationPolicy"
        )

        iam059da1c = iam.CfnRole(
            self,
            "iam059da1c",
            path="/",
            role_name="AWSCodeDeployRoleForECS-nightly",
            assume_role_policy_document="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"codedeploy.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}",
            max_session_duration=3600,
            managed_policy_arns=[
                "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS"
            ]
        )

        iam7c1bfd7 = iam.CfnPolicy(
            self,
            "iam7c1bfd7",
            policy_document='''
{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Resource": ["*"],
                "Action": [
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
                ]
            }
        ]
    }
''',
            roles=[
                "codebuild-outlier-service-codebuild-nightly-service-role"
            ],
            policy_name="CodeBuildBasePolicy"
        )


