# file: src/custom_constructs/pipeline_construct.py
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codedeploy as codedeploy,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    Duration,
)
from .base_construct import BaseConstruct


class PipelineConstruct(BaseConstruct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        service: ecs.FargateService,
        https_listener: elbv2.IApplicationListener,
        http_listener: elbv2.IApplicationListener,
        blue_target_group: elbv2.IApplicationTargetGroup,
        green_target_group: elbv2.IApplicationTargetGroup,
        application_name: str,
        deployment_group_name: str,
        pipeline_name: str,
        source_branch: str,
        repository_uri: str,
        service_name: str,
        buildspec_filename: str,
        appspec_filename: str,
        taskdef_filename: str,
        environment_value: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Create S3 bucket for build artifacts
        artifact_bucket = s3.Bucket(
            self,
            "ArtifactBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Define pipeline artifacts first
        source_output = codepipeline.Artifact()
        definition_artifact = codepipeline.Artifact("DefinitionArtifact")
        image_artifact = codepipeline.Artifact("ImageArtifact")

        # Create source action first
        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            action_name="GitHub",
            owner="outlier-org",
            repo="outlier-api",
            branch=source_branch,
            connection_arn="arn:aws:codeconnections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f",
            output=source_output,
        )

        # Create trigger configuration
        pipeline_trigger = codepipeline.Trigger(
            provider_type=codepipeline.ProviderType.CODE_STAR_SOURCE_CONNECTION,
            git_configuration=codepipeline.GitConfiguration(
                source_action=source_action,
                push_filter=[
                    codepipeline.GitPushFilter(branches_includes=[source_branch])
                ],
            ),
        )

        # Create pipeline with trigger
        pipeline = codepipeline.Pipeline(
            self,
            "Pipeline",
            artifact_bucket=artifact_bucket,
            pipeline_name=pipeline_name,
            triggers=[pipeline_trigger],
        )

        # Grant CodeStar connection permissions
        pipeline.role.add_to_policy(
            iam.PolicyStatement(
                actions=["codestar-connections:UseConnection"],
                resources=[
                    "arn:aws:codeconnections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f"
                ],
            )
        )

        # Initialize CodeDeploy application and deployment group
        codedeploy_app = codedeploy.EcsApplication(
            self, "CodeDeployApp", application_name=application_name
        )

        self._deployment_group = codedeploy.EcsDeploymentGroup(
            self,
            "CodeDeployGroup",
            application=codedeploy_app,
            service=service,
            deployment_group_name=deployment_group_name,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=https_listener,
                test_listener=http_listener,
                blue_target_group=blue_target_group,
                green_target_group=green_target_group,
                termination_wait_time=Duration.minutes(1),
            ),
        )

        # Configure CodeBuild project
        build_project = codebuild.PipelineProject(
            self,
            "BuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0, privileged=True
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=repository_uri
                ),
                "SERVICE_NAME": codebuild.BuildEnvironmentVariable(value=service_name),
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=environment_value
                ),
            },
            build_spec=codebuild.BuildSpec.from_source_filename(buildspec_filename),
        )

        # Grant ECR permissions to build project
        build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonEC2ContainerRegistryPowerUser"
            )
        )

        build_project.role.add_to_policy(
            iam.PolicyStatement(
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
                    "ecr:PutImage",
                ],
                resources=["*"],
            )
        )

        build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )

        # Add pipeline stages
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action],
        )

        pipeline.add_stage(
            stage_name="Build",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="Build",
                    project=build_project,
                    input=source_output,
                    outputs=[definition_artifact, image_artifact],
                )
            ],
        )

        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.CodeDeployEcsDeployAction(
                    action_name="Deploy",
                    deployment_group=self._deployment_group,
                    app_spec_template_file=definition_artifact.at_path(
                        appspec_filename
                    ),
                    task_definition_template_file=definition_artifact.at_path(
                        taskdef_filename
                    ),
                    container_image_inputs=[
                        codepipeline_actions.CodeDeployEcsContainerImageInput(
                            input=image_artifact,
                            task_definition_placeholder="IMAGE1_NAME",
                        )
                    ],
                )
            ],
        )

    @property
    def deployment_group(self) -> codedeploy.IEcsDeploymentGroup:
        return self._deployment_group
