# src/stacks/ecs_blue_green_stack.py
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

        # Security Groups
        self.alb_security_group = ec2.SecurityGroup(
            self, "AlbSecurityGroup-BlueGreen",
            vpc=self.vpc,
            description="Security group for Blue/Green ALB",
            allow_all_outbound=True
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(80),
            "Allow HTTP from anywhere"
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(8080),
            "Allow test traffic"
        )

        self.service_security_group = ec2.SecurityGroup(
            self, "ServiceSecurityGroup-BlueGreen",
            vpc=self.vpc,
            description="Security group for ECS Service",
            allow_all_outbound=True
        )
        self.service_security_group.add_ingress_rule(
            self.alb_security_group, ec2.Port.tcp(1337),
            "Allow from ALB"
        )

        # Load Balancer
        self.alb = elbv2.ApplicationLoadBalancer(
            self, "BlueGreenALB",
            vpc=self.vpc,
            internet_facing=True,
            security_group=self.alb_security_group,
            load_balancer_name="outlier-blue-green"
        )

        # Target Groups
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

        # Listeners
        self.prod_listener = self.alb.add_listener(
            "ProdListener", port=80,
            default_target_groups=[self.blue_target_group]
        )
        self.test_listener = self.alb.add_listener(
            "TestListener", port=8080,
            default_target_groups=[self.green_target_group]
        )

        # ECS Cluster
        self.cluster = ecs.Cluster(
            self, "BlueGreenCluster",
            vpc=self.vpc,
            cluster_name="outlier-blue-green"
        )

        # Task Execution Role
        task_execution_role = iam.Role.from_role_arn(
            self, "TaskExecutionRole",
            f"arn:aws:iam::{self.account}:role/ecsTaskExecutionRole"
        )
        task_execution_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "secretsmanager:GetSecretValue",
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            resources=["*"]
        ))

        # Placeholder Task Definition (structure only)
        task_definition = ecs.FargateTaskDefinition(
            self, "BlueGreenTaskDef",
            execution_role=task_execution_role,
            task_role=task_execution_role
        )

        # Placeholder Containers (actual config comes from JSON)
        task_definition.add_container(
            "AppContainer",
            image=ecs.ContainerImage.from_ecr_repository(
                ecr.Repository.from_repository_name(
                    self, "TempRepo", "outlier-ecr"
                ), "latest"
            )
        )
        task_definition.add_container(
            "DatadogContainer",
            image=ecs.ContainerImage.from_registry("datadog/agent:latest")
        )

        # ECS Service
        self.service = ecs.FargateService(
            self, "BlueGreenService",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=0,  # Critical initial state
            security_groups=[self.service_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            )
        )

        # CodeDeploy Setup
        codedeploy_app = codedeploy.EcsApplication(
            self, "CodeDeployApp",
            application_name="outlier-blue-green"
        )

        self.deployment_group = codedeploy.EcsDeploymentGroup(
            self, "CodeDeployGroup",
            application=codedeploy_app,
            service=self.service,
            deployment_group_name="outlier-blue-green",
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=self.prod_listener,
                test_listener=self.test_listener,
                blue_target_group=self.blue_target_group,
                green_target_group=self.green_target_group,
                termination_wait_time=Duration.minutes(5
                                                       )
            )

        # Pipeline Infrastructure
        artifact_bucket = s3.Bucket(
            self, "ArtifactBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        build_project = codebuild.PipelineProject(
            self, "BuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            ),
            environment_variables={
                "ECR_REPO": codebuild.BuildEnvironmentVariable(
                    value=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/outlier-ecr"
                )
            },
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec_nightly.yml")
        )
        build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryPowerUser")
        )
        build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )

        pipeline = codepipeline.Pipeline(
            self, "Pipeline",
            artifact_bucket=artifact_bucket,
            pipeline_name="outlier-blue-green-nightly"
        )

        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()

        # Pipeline Stages
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                codepipeline_actions.CodeStarConnectionsSourceAction(
                    action_name="GitHub",
                    owner="outlier-org",
                    repo="outlier-api",
                    branch="staging",
                    connection_arn="arn:aws:codestar-connections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f",
                    output=source_output
                )
            ]
        )

        pipeline.add_stage(
            stage_name="Build",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="Build",
                    project=build_project,
                    input=source_output,
                    outputs=[build_output]
                )
            ]
        )

        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.CodeDeployEcsDeployAction(
                    action_name="Deploy",
                    deployment_group=self.deployment_group,
                    app_spec_template_file=build_output.at_path("appspec_nightly.yaml"),
                    task_definition_template_file=build_output.at_path("taskdef_nightly.json"),
                    container_image_inputs=[
                        codepipeline_actions.CodeDeployEcsContainerImageInput(
                            input=build_output,
                            task_definition_placeholder="IMAGE1_NAME"
                        )
                    ]
                )
            ]
        )

        # Outputs
        cdk.CfnOutput(self, "ALBDnsName", value=self.alb.load_balancer_dns_name)