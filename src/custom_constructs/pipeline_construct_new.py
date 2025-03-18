import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codedeploy as codedeploy,
    aws_s3 as s3,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecs as ecs,
    Duration
)


class PipelineConstruct(Construct):
    def __init__(self, scope: Construct, id: str, service: ecs.FargateService,
                 https_listener: elbv2.IApplicationListener,
                 http_listener: elbv2.IApplicationListener,
                 blue_target_group: elbv2.IApplicationTargetGroup,
                 green_target_group: elbv2.IApplicationTargetGroup,
                 account: str, region: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # CodeDeploy Setup
        codedeploy_app = codedeploy.EcsApplication(
            self, "CodeDeployApp",
            application_name="outlier-blue-green"
        )

        self.deployment_group = codedeploy.EcsDeploymentGroup(
            self, "CodeDeployGroup",
            application=codedeploy_app,
            service=service,
            deployment_group_name="outlier-blue-green",
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=https_listener,
                test_listener=http_listener,
                blue_target_group=blue_target_group,
                green_target_group=green_target_group,
                termination_wait_time=Duration.minutes(1)
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
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=f"{account}.dkr.ecr.{region}.amazonaws.com/outlier-ecr-nightly"
                ),
                "SERVICE_NAME": codebuild.BuildEnvironmentVariable(
                    value="outlier-service-nightly"
                ),
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.environment.upper()
                )
            },
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec_nightly.yml")
        )

        build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryPowerUser")
        )

        # Add Custom ECR permissions
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

        build_project.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )

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
                    branch="nightly-taskdef-update",
                    connection_arn="arn:aws:codeconnections:us-east-1:528757783796:connection/ddd91232-5089-40b4-bc84-7ba9e4d1c20f",
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