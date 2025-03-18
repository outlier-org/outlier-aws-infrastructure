# src/stacks/dev_application_stack.py
class DevApplicationStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstructNew(
            self,
            "Network-Dev",  # resource-dev pattern
            suffix="dev"
        )

        # ECR Repository
        ecr = EcrConstructNew(
            self,
            "ECR-Dev",  # resource-dev pattern
            repository_name="outlier-ecr-dev"
        )

        # Load Balancer and DNS
        alb = AlbConstructNew(
            self,
            "LoadBalancer-Dev",  # resource-dev pattern
            vpc=network.vpc,
            security_group=network.alb_security_group,
            load_balancer_name="outlier-dev",
            subdomain="api.dev"
        )

        # Create and associate WAF
        waf = WafConstruct(
            self,
            "WAF-Dev",  # resource-dev pattern
            alb=alb.alb
        )

        # ECS Cluster, Service and Task Definition
        ecs = EcsConstructNew(
            self,
            "ECS-Dev",  # resource-dev pattern
            vpc=network.vpc,
            security_group=network.service_security_group,
            ecr_repository=ecr.repository,
            blue_target_group=alb.blue_target_group,
            desired_count=0,
            cluster_name="outlier-dev",
            container_name="Outlier-Service-Container-dev",
            log_group_name="/ecs/Outlier-Service-dev"
        )

        # CI/CD Pipeline
        pipeline = PipelineConstructNew(
            self,
            "Pipeline-Dev",  # resource-dev pattern
            service=ecs.service,
            https_listener=alb.https_listener,
            http_listener=alb.http_listener,
            blue_target_group=alb.blue_target_group,
            green_target_group=alb.green_target_group,
            application_name="outlier-dev",
            deployment_group_name="outlier-dev",
            pipeline_name="outlier-dev",
            source_branch="staging",
            repository_uri=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/outlier-ecr-dev",
            service_name="outlier-service-dev",
            buildspec_filename="buildspec_nightly.yml",
            appspec_filename="appspec_nightly.yaml",
            taskdef_filename="taskdef_nightly.json"
        )

        # Outputs
        cdk.CfnOutput(self, "ALBDnsName-Dev", value=alb.alb.load_balancer_dns_name)