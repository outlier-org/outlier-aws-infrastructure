import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_codedeploy as codedeploy,
    aws_elasticloadbalancingv2 as elbv2,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_logs as logs,
    aws_s3 as s3,
    Duration,
)

class EcsBlueGreenStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Existing VPC
        self.vpc = ec2.Vpc.from_lookup(
            self, "ExistingVPC",
            vpc_id="vpc-00059e30c80aa84f2"
        )

        # Import existing RDS Security Group
        self.rds_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            "ExistingRdsSecurityGroup",
            "sg-05fcdaf33c1d2a016",
            allow_all_outbound=True
        )

        # Security Groups
        self.alb_security_group = ec2.SecurityGroup(
            self, "AlbSecurityGroup-BlueGreen",
            vpc=self.vpc,
            security_group_name=f"outlier-alb-bluegreen-{self.environment}-sg",
            description="Security group for Blue/Green ALB",
            allow_all_outbound=True
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(80),
            "Allow HTTP from anywhere"
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.tcp(8080),
            "Allow test traffic from within VPC"
        )

        self.service_security_group = ec2.SecurityGroup(
            self, "ServiceSecurityGroup-BlueGreen",
            vpc=self.vpc,
            security_group_name=f"outlier-service-bluegreen-{self.environment}-sg",
            description="Security group for ECS Service",
            allow_all_outbound=True
        )
        self.service_security_group.add_ingress_rule(
            self.alb_security_group, ec2.Port.tcp(1337),
            "Allow from ALB"
        )

        # Add RDS ingress rule to allow access FROM our service security group
        self.rds_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.service_security_group.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from ECS service"
        )

        # Load Balancer
        self.alb = elbv2.ApplicationLoadBalancer(
            self, "BlueGreenALB",
            vpc=self.vpc,
            internet_facing=True,
            security_group=self.alb_security_group,
            load_balancer_name="outlier-blue-green"
        )

        # Target Groups for Main Service
        self.blue_target_group = elbv2.ApplicationTargetGroup(
            self, "BlueTargetGroup",
            vpc=self.vpc,
            port=1337,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )
        self.green_target_group = elbv2.ApplicationTargetGroup(
            self, "GreenTargetGroup",
            vpc=self.vpc,
            port=1337,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        # Target Groups for Jobs Service
        self.jobs_blue_target_group = elbv2.ApplicationTargetGroup(
            self, "JobsBlueTargetGroup",
            vpc=self.vpc,
            port=1337,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )
        self.jobs_green_target_group = elbv2.ApplicationTargetGroup(
            self, "JobsGreenTargetGroup",
            vpc=self.vpc,
            port=1337,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        # Listener for Main Service (unchanged)
        self.prod_listener = self.alb.add_listener(
            "ProdListener", port=80,
            default_target_groups=[self.blue_target_group]
        )
        self.test_listener = self.alb.add_listener(
            "TestListener", port=8080,
            default_target_groups=[self.green_target_group]
        )

        # Listener Rule for Jobs Service
        self.prod_listener.add_action(
            "JobsPathRule",
            priority=10,
            conditions=[elbv2.ListenerCondition.path_patterns(["/jobs/*"])],
            action=elbv2.ListenerAction.forward([self.jobs_blue_target_group])
        )

        # ECS Cluster (unchanged)
        self.cluster = ecs.Cluster(
            self, "BlueGreenCluster",
            vpc=self.vpc,
            cluster_name="outlier-blue-green"
        )

        # Task Execution Role (unchanged)
        task_execution_role = iam.Role.from_role_arn(
            self, "TaskExecutionRole",
            f"arn:aws:iam::{self.account}:role/ecsTaskExecutionRole"
        )
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

        self.ecr_repository = ecr.Repository(
            self,
            "OutlierEcrRepo-Nightly",
            repository_name="outlier-ecr-nightly",
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Delete when imageCountMoreThan (10)",
                    max_image_count=10,
                    rule_priority=1,
                    tag_status=ecr.TagStatus.ANY
                )
            ],
        )

        # Log Group for Main Service
        main_log_group = logs.LogGroup(
            self,
            "MainEcsLogGroup",
            log_group_name="/ecs/Outlier-Main-Service-nightly",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        # Log Group for Jobs Service
        jobs_log_group = logs.LogGroup(
            self,
            "JobsEcsLogGroup",
            log_group_name="/ecs/Outlier-Jobs-Service-nightly",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        # Main Service Task Definition
        main_task_definition = ecs.FargateTaskDefinition(
            self, "MainTaskDef",
            execution_role=task_execution_role,
            task_role=task_execution_role,
            cpu=2048,  # 2 vCPU
            memory_limit_mib=4096  # 4GB
        )
        main_container = main_task_definition.add_container(
            "Outlier-Main-Container-nightly",
            image=ecs.ContainerImage.from_ecr_repository(
                self.ecr_repository,
                tag="latest"
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_group=main_log_group
            )
        )
        main_container.add_port_mappings(ecs.PortMapping(container_port=1337))
        self.main_service = ecs.FargateService(
            self, "MainService",
            cluster=self.cluster,
            task_definition=main_task_definition,
            desired_count=1,
            security_groups=[self.service_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            )
        )
        self.main_service.attach_to_application_target_group(self.blue_target_group)

        # Jobs Service Task Definition
        jobs_task_definition = ecs.FargateTaskDefinition(
            self, "JobsTaskDef",
            execution_role=task_execution_role,
            task_role=task_execution_role,
            cpu=2048,  # 2 vCPU
            memory_limit_mib=4096  # 4GB
        )
        jobs_container = jobs_task_definition.add_container(
            "Outlier-Jobs-Container-nightly",
            image=ecs.ContainerImage.from_ecr_repository(
                self.ecr_repository,  # Use the newly created ECR repository
                tag="latest"
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_group=jobs_log_group
            )
        )
        jobs_container.add_port_mappings(ecs.PortMapping(container_port=1337))
        self.jobs_service = ecs.FargateService(
            self, "JobsService",
            cluster=self.cluster,
            task_definition=jobs_task_definition,
            desired_count=0,  # Start with 0 tasks
            security_groups=[self.service_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            )
        )
        self.jobs_service.attach_to_application_target_group(self.jobs_blue_target_group)

        # CodeDeploy for Main Service (unchanged)
        main_codedeploy_app = codedeploy.EcsApplication(
            self, "MainCodeDeployApp",
            application_name="outlier-main-service-nightly"
        )
        self.main_deployment_group = codedeploy.EcsDeploymentGroup(
            self, "MainCodeDeployGroup",
            application=main_codedeploy_app,
            service=self.main_service,
            deployment_group_name="outlier-main-service-nightly",
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=self.prod_listener,
                test_listener=self.test_listener,
                blue_target_group=self.blue_target_group,
                green_target_group=self.green_target_group,
                termination_wait_time=Duration.minutes(1)
            )
        )

        # CodeDeploy for Jobs Service
        jobs_codedeploy_app = codedeploy.EcsApplication(
            self, "JobsCodeDeployApp",
            application_name="outlier-jobs-service-nightly"
        )
        self.jobs_deployment_group = codedeploy.EcsDeploymentGroup(
            self, "JobsCodeDeployGroup",
            application=jobs_codedeploy_app,
            service=self.jobs_service,
            deployment_group_name="outlier-jobs-service-nightly",
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=self.prod_listener,
                test_listener=self.test_listener,
                blue_target_group=self.jobs_blue_target_group,
                green_target_group=self.jobs_green_target_group,
                termination_wait_time=Duration.minutes(1)
            )
        )

        # Pipeline Infrastructure
        artifact_bucket = s3.Bucket(
            self, "ArtifactBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # CodeBuild Project for Main Service
        main_build_project = codebuild.PipelineProject(
            self, "MainBuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/outlier-ecr-nightly"
                ),
                "SERVICE_NAME": codebuild.BuildEnvironmentVariable(
                    value="outlier-main-service-nightly"
                ),
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.environment.upper()
                )
            },
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec_nightly.yml")
        )
        main_build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryPowerUser")
        )
        main_build_project.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:GetRepositoryPolicy",
                "ecr:ListImages",
                "ecr:DescribeRepositories",
                "ecr:ListTagsForResource",
                "ecr:DescribeImages",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            resources=["*"]
        ))
        main_build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )

        # CodeBuild Project for Jobs Service
        jobs_build_project = codebuild.PipelineProject(
            self, "JobsBuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/outlier-ecr-nightly"
                ),
                "SERVICE_NAME": codebuild.BuildEnvironmentVariable(
                    value="outlier-jobs-service-nightly"
                ),
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.environment.upper()
                )
            },
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec_nightly.yml")
        )
        jobs_build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryPowerUser")
        )
        jobs_build_project.role.add_to_policy(iam.PolicyStatement(
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:GetRepositoryPolicy",
                "ecr:ListImages",
                "ecr:DescribeRepositories",
                "ecr:ListTagsForResource",
                "ecr:DescribeImages",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            resources=["*"]
        ))
        jobs_build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )

        # CodePipeline
        pipeline = codepipeline.Pipeline(
            self, "Pipeline",
            artifact_bucket=artifact_bucket,
            pipeline_name="outlier-blue-green-nightly"
        )

        # Add CodeStar connection permissions to pipeline role
        pipeline.role.add_to_policy(iam.PolicyStatement(
            actions=["codestar-connections:UseConnection"],
            resources=["arn:aws:codeconnections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f"]
        ))

        # Source Stage (unchanged)
        source_output = codepipeline.Artifact()
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                codepipeline_actions.CodeStarConnectionsSourceAction(
                    action_name="GitHub",
                    owner="outlier-org",
                    repo="outlier-api",
                    branch="nightly-taskdef-update",
                    connection_arn="arn:aws:codeconnections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f",
                    output=source_output
                )
            ]
        )

        # Build Stage for Main Service
        main_build_output = codepipeline.Artifact()
        pipeline.add_stage(
            stage_name="BuildMain",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="BuildMain",
                    project=main_build_project,
                    input=source_output,
                    outputs=[main_build_output]
                )
            ]
        )

        # Build Stage for Jobs Service
        jobs_build_output = codepipeline.Artifact()
        pipeline.add_stage(
            stage_name="BuildJobs",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="BuildJobs",
                    project=jobs_build_project,
                    input=source_output,
                    outputs=[jobs_build_output]
                )
            ]
        )

        # Deploy Stage for Main Service
        pipeline.add_stage(
            stage_name="DeployMain",
            actions=[
                codepipeline_actions.CodeDeployEcsDeployAction(
                    action_name="DeployMain",
                    deployment_group=self.main_deployment_group,
                    app_spec_template_file=main_build_output.at_path("appspec_nightly.yaml"),
                    task_definition_template_file=main_build_output.at_path("taskdef_nightly.json"),
                    container_image_inputs=[
                        codepipeline_actions.CodeDeployEcsContainerImageInput(
                            input=main_build_output,
                            task_definition_placeholder="IMAGE1_NAME"
                        )
                    ]
                )
            ]
        )

        # Deploy Stage for Jobs Service
        pipeline.add_stage(
            stage_name="DeployJobs",
            actions=[
                codepipeline_actions.CodeDeployEcsDeployAction(
                    action_name="DeployJobs",
                    deployment_group=self.jobs_deployment_group,
                    app_spec_template_file=jobs_build_output.at_path("appspec_job_nightly.yaml"),
                    task_definition_template_file=jobs_build_output.at_path("taskdef_job_nightly.json"),
                    container_image_inputs=[
                        codepipeline_actions.CodeDeployEcsContainerImageInput(
                            input=jobs_build_output,
                            task_definition_placeholder="IMAGE1_NAME"
                        )
                    ]
                )
            ]
        )

        # Outputs
        cdk.CfnOutput(self, "ALBDnsName", value=self.alb.load_balancer_dns_name)