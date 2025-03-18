# src/custom_constructs/pipeline_construct_new.py
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
    Duration
)
from .base_construct import BaseConstruct


class PipelineConstructNew(BaseConstruct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            service: ecs.FargateService,
            https_listener: elbv2.IApplicationListener,
            http_listener: elbv2.IApplicationListener,
            blue_target_group: elbv2.IApplicationTargetGroup,
            green_target_group: elbv2.IApplicationTargetGroup,
            application_name: str = "outlier-blue-green",
            deployment_group_name: str = "outlier-blue-green",
            pipeline_name: str = "outlier-blue-green-nightly",
            source_branch: str = "feat/OUTL-2068-Creade-a-module-to-sync-Realize-Roster-updates-to-Outlier",
            repository_uri: str = None,
            service_name: str = "outlier-service-nightly",
            buildspec_filename: str = "buildspec_nightly.yml",
            appspec_filename: str = "appspec_nightly.yaml",
            taskdef_filename: str = "taskdef_nightly.json",
            **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Store parameters
        self.application_name = application_name
        self.deployment_group_name = deployment_group_name
        self.pipeline_name = pipeline_name
        self.source_branch = source_branch
        self.repository_uri = repository_uri or f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/outlier-ecr-nightly"
        self.service_name = service_name
        self.buildspec_filename = buildspec_filename
        self.appspec_filename = appspec_filename
        self.taskdef_filename = taskdef_filename

        # CodeDeploy Setup - identical to original but parameterized
        codedeploy_app = codedeploy.EcsApplication(
            self, "CodeDeployApp",
            application_name=self.application_name
        )

        self._deployment_group = codedeploy.EcsDeploymentGroup(
            self, "CodeDeployGroup",
            application=codedeploy_app,
            service=service,
            deployment_group_name=self.deployment_group_name,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=https_listener,
                test_listener=http_listener,
                blue_target_group=blue_target_group,
                green_target_group=green_target_group,
                termination_wait_time=Duration.minutes(1)  # Same as original
            )
        )

        # Pipeline Infrastructure - identical to original
        artifact_bucket = s3.Bucket(
            self, "ArtifactBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Build project - identical to original but parameterized
        build_project = codebuild.PipelineProject(
            self, "BuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=self.repository_uri
                ),
                "SERVICE_NAME": codebuild.BuildEnvironmentVariable(
                    value=self.service_name
                ),
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.environment.upper()
                )
            },
            build_spec=codebuild.BuildSpec.from_source_filename(self.buildspec_filename)
        )

        # Same policies as original
        build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryPowerUser")
        )

        # Add Custom ECR permissions - identical to original
        build_project.role.add_to_policy(iam.PolicyStatement(
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

        # Same policy as original
        build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )

        # Pipeline - identical to original but parameterized
        pipeline = codepipeline.Pipeline(
            self, "Pipeline",
            artifact_bucket=artifact_bucket,
            pipeline_name=self.pipeline_name
        )

        # Add CodeStar connection - identical to original
        pipeline.role.add_to_policy(iam.PolicyStatement(
            actions=["codestar-connections:UseConnection"],
            resources=["arn:aws:codeconnections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f"]
        ))

        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()

        # Pipeline Source Stage - identical but parameterized branch
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                codepipeline_actions.CodeStarConnectionsSourceAction(
                    action_name="GitHub",
                    owner="outlier-org",
                    repo="outlier-api",
                    branch=self.source_branch,  # Parameterized to "staging"
                    connection_arn="arn:aws:codeconnections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f",
                    output=source_output
                )
            ]
        )

        # Pipeline Build Stage - identical to original
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

        # Pipeline Deploy Stage - identical but parameterized filenames
        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.CodeDeployEcsDeployAction(
                    action_name="Deploy",
                    deployment_group=self._deployment_group,
                    app_spec_template_file=build_output.at_path(self.appspec_filename),
                    task_definition_template_file=build_output.at_path(self.taskdef_filename),
                    container_image_inputs=[
                        codepipeline_actions.CodeDeployEcsContainerImageInput(
                            input=build_output,
                            task_definition_placeholder="IMAGE1_NAME"
                        )
                    ]
                )
            ]
        )

    @property
    def deployment_group(self) -> codedeploy.IEcsDeploymentGroup:
        return self._deployment_group