# src/custom_constructs/pipeline_construct.py
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codedeploy as codedeploy
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_s3 as s3
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
            ecr_repository: ecr.IRepository
    ):
        super().__init__(scope, id)

        # Pipeline Role
        pipeline_role = iam.Role(
            self,
            "PipelineRole",
            role_name=f"AWSCodePipelineServiceRole-{self.environment}-test",
            assumed_by=iam.ServicePrincipal("codepipeline.amazonaws.com")
        )

        # CodeBuild Role
        codebuild_role = iam.Role(
            self,
            "CodeBuildRole",
            role_name=f"codebuild-outlier-service-codebuild-{self.environment}-test-service-role",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com")
        )

        # CodeBuild Project
        build_project = codebuild.Project(
            self,
            "CodeBuildProject",
            project_name=f"outlier-service-codebuild-{self.environment}-test",
            build_spec=codebuild.BuildSpec.from_source_filename(f"buildspec_{self.environment}.yml"),
            environment=codebuild.BuildEnvironment(
                compute_type=codebuild.ComputeType.SMALL,
                image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5,
                privileged=True,
                environment_variables={
                    "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                        value=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/{ecr_repository.repository_name}"
                    ),
                    "SERVICE_NAME": codebuild.BuildEnvironmentVariable(
                        value=f"outlier-service-{self.environment}-test"
                    ),
                    "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                        value=self.environment.upper()
                    )
                }
            ),
            role=codebuild_role,
            timeout=cdk.Duration.minutes(60),
            queue_timeout=cdk.Duration.minutes(480)
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

        # CodeDeploy Deployment Groups
        service_deployment_group = codedeploy.EcsDeploymentGroup(
            self,
            "ServiceDeploymentGroup",
            application=service_app,
            deployment_group_name=f"outlier-service-deployment-group-{self.environment}-test",
            deployment_config=codedeploy.EcsDeploymentConfig.ALL_AT_ONCE,
            service=ecs_service,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                deployment_approval_wait_time=cdk.Duration.minutes(0),
                listener=None,  # Will be configured in ECS service
                terminate_blue_tasks_on_deployment_success=codedeploy.EcsBlueGreenDeploymentTerminationConfig(
                    termination_wait_time=cdk.Duration.minutes(5)
                )
            )
        )

        jobs_deployment_group = codedeploy.EcsDeploymentGroup(
            self,
            "JobsDeploymentGroup",
            application=jobs_app,
            deployment_group_name=f"outlier-job-deployment-group-{self.environment}-test",
            deployment_config=codedeploy.EcsDeploymentConfig.ALL_AT_ONCE,
            service=ecs_jobs_service,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                deployment_approval_wait_time=cdk.Duration.minutes(0),
                listener=None,
                terminate_blue_tasks_on_deployment_success=codedeploy.EcsBlueGreenDeploymentTerminationConfig(
                    termination_wait_time=cdk.Duration.minutes(5)
                )
            )
        )

        # Artifact Bucket
        artifact_bucket = s3.Bucket.from_bucket_name(
            self,
            "ArtifactBucket",
            f"codepipeline-us-east-1-{self.environment}-test-1737061688"
        )

        # Pipeline
        self.pipeline = codepipeline.Pipeline(
            self,
            "Pipeline",
            pipeline_name=f"outlier-service-codepipeline-{self.environment}-test",
            role=pipeline_role,
            artifact_bucket=artifact_bucket
        )

        source_output = codepipeline.Artifact("SourceArtifact")
        build_output = codepipeline.Artifact("BuildArtifact")

        # Add Source Stage
        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            action_name="Source",
            owner="outlier-org",
            repo="outlier-api",
            branch=f"{self.environment}-aws-infra-changes",
            connection_arn="arn:aws:codeconnections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f",
            output=source_output
        )
        self.pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # Add Build Stage
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

        # Add Deploy Stage
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
            container_image_inputs=[{
                "input": build_output,
                "taskDefinitionPlaceholder": "IMAGE1_NAME"
            }]
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
            container_image_inputs=[{
                "input": build_output,
                "taskDefinitionPlaceholder": "IMAGE1_NAME"
            }]
        )

        self.pipeline.add_stage(
            stage_name="Deploy",
            actions=[service_deploy_action, jobs_deploy_action]
        )