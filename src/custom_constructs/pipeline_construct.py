# src/custom_constructs/pipeline_construct.py
from aws_cdk import (
    aws_codebuild as codebuild,
    aws_codedeploy as codedeploy,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_s3 as s3,
    Duration
)
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class CodePipelineConstruct(BaseConstruct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            ecs_cluster: ecs.ICluster,
            ecs_service: ecs.IService,
            ecs_jobs_service: ecs.IService,
            prod_listener: elbv2.IApplicationListener,
            test_listener: elbv2.IApplicationListener,
            service_target_groups: list[elbv2.IApplicationTargetGroup],
            jobs_target_groups: list[elbv2.IApplicationTargetGroup]
    ):
        super().__init__(scope, id)

        # Create ECR Repository
        self.repository = ecr.Repository(
            self,
            "OutlierEcr",
            repository_name=f"outlier-ecr-{self.environment}-test",
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep only 10 images",
                    max_image_count=10,
                    rule_priority=1,
                    tag_status=ecr.TagStatus.ANY
                )
            ],
            removal_policy=cdk.RemovalPolicy.RETAIN
        )

        # Pipeline Role with required permissions
        pipeline_role = iam.Role(
            self,
            "PipelineRole",
            role_name=f"AWSCodePipelineServiceRole-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("codepipeline.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodePipelineServiceRole")
            ]
        )

        pipeline_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "elasticloadbalancing:*",
                    "ecs:*",
                    "codedeploy:*",
                    "s3:*",
                    "ecr:*"
                ],
                resources=["*"]
            )
        )

        # CodeBuild Project
        build_project = codebuild.PipelineProject(
            self,
            "CodeBuildProject",
            project_name=f"outlier-service-codebuild-{self.environment}-test",
            build_spec=codebuild.BuildSpec.from_source_filename(f"buildspec_{self.environment}.yml"),
            environment=codebuild.BuildEnvironment(
                compute_type=codebuild.ComputeType.SMALL,
                privileged=True,
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/{self.repository.repository_name}"
                ),
                "SERVICE_NAME": codebuild.BuildEnvironmentVariable(
                    value=f"outlier-service-{self.environment}-test"
                ),
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.environment.upper()
                )
            },
            timeout=Duration.minutes(60),
            queue_timeout=Duration.minutes(480),
            cache=codebuild.Cache.local(codebuild.LocalCacheMode.DOCKER_LAYER)
        )

        # CodeDeploy Applications
        service_app = codedeploy.EcsApplication(
            self,
            "ServiceCodeDeployApp",
            application_name=f"outlier-service-codedeploy-{self.environment}-test"
        )

        jobs_app = codedeploy.EcsApplication(
            self,
            "JobsCodeDeployApp",
            application_name=f"outlier-jobs-codedeploy-{self.environment}-test"
        )

        # Deployment Groups
        service_deployment_group = codedeploy.EcsDeploymentGroup(
            self,
            "ServiceDeploymentGroup",
            application=service_app,
            deployment_group_name=f"outlier-service-deployment-group-{self.environment}-test",
            deployment_config=codedeploy.EcsDeploymentConfig.ALL_AT_ONCE,
            service=ecs_service,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=prod_listener,
                test_listener=test_listener,
                blue_target_group=service_target_groups[0],
                green_target_group=service_target_groups[1],
                deployment_approval_wait_time=Duration.minutes(0),
                terminate_blue_tasks_on_deployment_success=codedeploy.EcsBlueGreenDeploymentTerminationConfig(
                    action=codedeploy.EcsBlueGreenTerminationAction.TERMINATE,
                    termination_wait_time=Duration.minutes(5)
                )
            )
        )

        jobs_deployment_group = codedeploy.EcsDeploymentGroup(
            self,
            "JobsDeploymentGroup",
            application=jobs_app,
            deployment_group_name=f"outlier-jobs-deployment-group-{self.environment}-test",
            deployment_config=codedeploy.EcsDeploymentConfig.ALL_AT_ONCE,
            service=ecs_jobs_service,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=prod_listener,
                test_listener=test_listener,
                blue_target_group=jobs_target_groups[0],
                green_target_group=jobs_target_groups[1],
                deployment_approval_wait_time=Duration.minutes(0),
                terminate_blue_tasks_on_deployment_success=codedeploy.EcsBlueGreenDeploymentTerminationConfig(
                    action=codedeploy.EcsBlueGreenTerminationAction.TERMINATE,
                    termination_wait_time=Duration.minutes(5)
                )
            )
        )

        # Artifact Bucket
        artifact_bucket = s3.Bucket(
            self,
            "ArtifactBucket",
            bucket_name=f"codepipeline-{self.region}-{self.environment}-test-{self.account}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Pipeline Setup
        self.pipeline = codepipeline.Pipeline(
            self,
            "Pipeline",
            pipeline_name=f"outlier-service-codepipeline-{self.environment}-test",
            role=pipeline_role,
            artifact_bucket=artifact_bucket
        )

        source_output = codepipeline.Artifact("SourceArtifact")
        build_output = codepipeline.Artifact("BuildArtifact")

        # Source Stage
        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            action_name="Source",
            owner="outlier-org",
            repo="outlier-api",
            branch=f"{self.environment}-aws-infra-changes",
            connection_arn="arn:aws:codestar-connections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f",
            output=source_output,
            trigger_on_push=True
        )
        self.pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # Build Stage
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="Build",
            project=build_project,
            input=source_output,
            outputs=[build_output]
        )
        self.pipeline.add_stage(
            stage_name="Build",
            actions=[build_action]
        )

        # Deploy Stage
        service_deploy_action = codepipeline_actions.CodeDeployEcsDeployAction(
            action_name="OutlierServiceDeployment",
            service=ecs_service,
            deployment_group=service_deployment_group,
            app_spec_template_file=codepipeline.ArtifactPath(
                build_output,
                f"appspec_{self.environment}.yaml"
            ),
            task_definition_template_file=codepipeline.ArtifactPath(
                build_output,
                f"taskdef_{self.environment}.json"
            ),
            container_image_inputs=[
                codepipeline_actions.CodeDeployEcsContainerImageInput(
                    input=build_output,
                    task_definition_placeholder="IMAGE1_NAME"
                )
            ],
            run_order=1
        )

        jobs_deploy_action = codepipeline_actions.CodeDeployEcsDeployAction(
            action_name="OutlierJobDeployment",
            service=ecs_jobs_service,
            deployment_group=jobs_deployment_group,
            app_spec_template_file=codepipeline.ArtifactPath(
                build_output,
                f"appspec_job_{self.environment}.yaml"
            ),
            task_definition_template_file=codepipeline.ArtifactPath(
                build_output,
                f"taskdef_job_{self.environment}.json"
            ),
            container_image_inputs=[
                codepipeline_actions.CodeDeployEcsContainerImageInput(
                    input=build_output,
                    task_definition_placeholder="IMAGE1_NAME"
                )
            ],
            run_order=2
        )

        self.pipeline.add_stage(
            stage_name="Deploy",
            actions=[service_deploy_action, jobs_deploy_action]
        )

    @property
    def ecr_repository(self) -> ecr.IRepository:
        return self.repository