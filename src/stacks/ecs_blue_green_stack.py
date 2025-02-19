# src/stacks/ecs_blue_green_stack.py
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_codedeploy as codedeploy,
    aws_elasticloadbalancingv2 as elbv2,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_logs as logs,
    Duration,
)

class EcsBlueGreenStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Use existing VPC
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "ExistingVPC",
            vpc_id="vpc-00059e30c80aa84f2"
        )

        # Security Groups
        self.alb_security_group = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup-BlueGreen",
            vpc=self.vpc,
            security_group_name=f"outlier-alb-blue-green-{self.environment}-sg",
            description="Security group for Blue/Green ALB"
        )

        self.service_security_group = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup-BlueGreen",
            vpc=self.vpc,
            security_group_name=f"outlier-service-blue-green-{self.environment}-sg",
            description="Security group for Blue/Green ECS Service"
        )

        # Security group rules
        self.alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from anywhere"
        )

        self.alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from anywhere"
        )

        self.service_security_group.add_ingress_rule(
            peer=self.alb_security_group,
            connection=ec2.Port.tcp(1337),  # Match the port in taskdef_nightly.json
            description="Allow traffic from ALB"
        )

        # Create ALB
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "BlueGreenALB",
            vpc=self.vpc,
            internet_facing=True,
            security_group=self.alb_security_group,
            load_balancer_name=f"outlier-blue-green-{self.environment}-alb"
        )

        # Create blue/green target groups
        self.blue_target_group = elbv2.ApplicationTargetGroup(
            self,
            "BlueTargetGroup",
            vpc=self.vpc,
            port=1337,  # Match the port in taskdef_nightly.json
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",  # Match the health check path in the application
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        self.green_target_group = elbv2.ApplicationTargetGroup(
            self,
            "GreenTargetGroup",
            vpc=self.vpc,
            port=1337,  # Match the port in taskdef_nightly.json
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",  # Match the health check path in the application
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        # Create production listener
        self.prod_listener = self.alb.add_listener(
            "ProdListener",
            port=80,
            default_target_groups=[self.blue_target_group]
        )

        # Create test listener
        self.test_listener = self.alb.add_listener(
            "TestListener",
            port=8080,
            default_target_groups=[self.green_target_group]
        )

        # Create ECS Cluster
        self.cluster = ecs.Cluster(
            self,
            "BlueGreenCluster",
            vpc=self.vpc,
            cluster_name=f"outlier-blue-green-{self.environment}-cluster"
        )

        # Use existing task execution role
        task_execution_role = iam.Role.from_role_arn(
            self,
            "ExistingTaskExecutionRole",
            f"arn:aws:iam::{self.account}:role/ecsTaskExecutionRole-{self.environment}-test"
        )

        # Use existing task role
        task_role = iam.Role.from_role_arn(
            self,
            "ExistingTaskRole",
            f"arn:aws:iam::{self.account}:role/ecsTaskRole-{self.environment}-test"
        )

        # Log group for ECS tasks
        log_group = logs.LogGroup(
            self,
            "ServiceLogGroup",
            log_group_name=f"/ecs/Outlier-Service-{self.environment}",
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        # Task Definition (matching taskdef_nightly.json)
        task_definition = ecs.FargateTaskDefinition(
            self,
            "BlueGreenTaskDef",
            family=f"Outlier-Service-Task-{self.environment}",
            cpu=2048,
            memory_limit_mib=4096,
            execution_role=task_execution_role,
            task_role=task_role
        )

        # Add containers matching taskdef_nightly.json
        container = task_definition.add_container(
            "ServiceContainer",
            image=ecs.ContainerImage.from_registry(f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/outlier-ecr:latest"),
            cpu=1536,
            memory_limit_mib=3072,
            memory_reservation_mib=2560,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=log_group
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:1337/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3
            ),
            environment={
                "NODE_ENV": "production",
                "CLOUD_PROVIDER": "AWS",
                "DATADOG_SERVICE": "outlier-service"
            }
        )

        container.add_port_mappings(
            ecs.PortMapping(
                container_port=1337,
                host_port=1337,
                protocol=ecs.Protocol.TCP
            )
        )

        # ECS Service
        self.service = ecs.FargateService(
            self,
            "BlueGreenService",
            cluster=self.cluster,
            task_definition=task_definition,
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            ),
            desired_count=2,
            security_groups=[self.service_security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        # CodeBuild Project
        build_project = codebuild.PipelineProject(
            self,
            "BuildProject",
            project_name=f"outlier-blue-green-{self.environment}",
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec_nightly.yml"),
            environment=codebuild.BuildEnvironment(
                privileged=True,
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/outlier-ecr"
                ),
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.environment.upper()
                )
            }
        )

        # CodeDeploy Application
        self.app = codedeploy.EcsApplication(
            self,
            "BlueGreenApp",
            application_name=f"outlier-blue-green-{self.environment}-app"
        )

        # CodeDeploy Deployment Group
        self.deployment_group = codedeploy.EcsDeploymentGroup(
            self,
            "BlueGreenDeploymentGroup",
            application=self.app,
            service=self.service,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=self.prod_listener,
                test_listener=self.test_listener,
                blue_target_group=self.blue_target_group,
                green_target_group=self.green_target_group
            )
        )

        # Pipeline
        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()

        pipeline = codepipeline.Pipeline(
            self,
            "Pipeline",
            pipeline_name=f"outlier-blue-green-{self.environment}-pipeline"
        )

        # Source Stage
        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            action_name="GitHub",
            owner="outlier-org",
            repo="outlier-api",
            branch="staging",  # Use staging branch as requested
            connection_arn="arn:aws:codestar-connections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f",
            output=source_output
        )

        # Build Stage
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="Build",
            project=build_project,
            input=source_output,
            outputs=[build_output]
        )

        # Deploy Stage
        deploy_action = codepipeline_actions.CodeDeployEcsDeployAction(
            action_name="Deploy",
            deployment_group=self.deployment_group,
            app_spec_template_file=source_output.at_path("appspec_nightly.yaml"),
            task_definition_template_file=source_output.at_path("taskdef_nightly.json"),
            container_image_inputs=[
                codepipeline_actions.CodeDeployEcsContainerImageInput(
                    input=build_output,
                    task_definition_placeholder="IMAGE1_NAME"
                )
            ]
        )

        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        pipeline.add_stage(
            stage_name="Build",
            actions=[build_action]
        )

        pipeline.add_stage(
            stage_name="Deploy",
            actions=[deploy_action]
        )