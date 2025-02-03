# src/custom_constructs/alb_construct.py
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_certificatemanager as acm
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class AlbConstruct(BaseConstruct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            vpc: ec2.IVpc,
            security_group: ec2.ISecurityGroup,
            subnets: list[ec2.ISubnet]
    ):
        super().__init__(scope, id)

        # Import existing certificate
        certificate = acm.Certificate.from_certificate_arn(
            self,
            "AlbCertificate",
            "arn:aws:acm:us-east-1:528757783796:certificate/a9387ff3-5327-448e-b1a2-3ca8e3e1e7f4"
        )

        # Create ALB
        self.load_balancer = elbv2.ApplicationLoadBalancer(
            self,
            "ApplicationLoadBalancer",
            load_balancer_name=f"outlier-service-alb-{self.environment}-test",
            vpc=vpc,
            internet_facing=True,
            security_group=security_group,
            vpc_subnets=ec2.SubnetSelection(subnets=subnets),
            idle_timeout=cdk.Duration.seconds(60),
            http2_enabled=True,
            deletion_protection=False
        )

        # Create Target Groups
        self.service_target_group = elbv2.ApplicationTargetGroup(
            self,
            "ServiceTargetGroup",
            target_group_name=f"outlier-service-tg-2-{self.environment}-test",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                healthy_http_codes="200-499",
                interval=cdk.Duration.seconds(30)
            ),
            deregistration_delay=cdk.Duration.seconds(300)
        )

        self.jobs_target_group = elbv2.ApplicationTargetGroup(
            self,
            "JobsTargetGroup",
            target_group_name=f"outlier-job-service-tg-1-{self.environment}-test",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                healthy_http_codes="200-499",
                interval=cdk.Duration.seconds(30)
            ),
            deregistration_delay=cdk.Duration.seconds(300)
        )

        # Add HTTP Listener
        http_listener = self.load_balancer.add_listener(
            "HttpListener",
            port=80,
            default_target_groups=[self.service_target_group]
        )

        # Add HTTPS Listener
        https_listener = self.load_balancer.add_listener(
            "HttpsListener",
            port=443,
            certificates=[certificate],
            ssl_policy=elbv2.SslPolicy.TLS13_1_2_2021_06,
            default_target_groups=[self.service_target_group]
        )

        # Add listener rules for jobs
        https_listener.add_target_groups(
            "CronRule",
            priority=1,
            conditions=[
                elbv2.ListenerCondition.path_patterns([
                    "/cron-script",
                    "/cron-script/*",
                    "/test-cron",
                    "/test-cron/*"
                ])
            ],
            target_groups=[self.jobs_target_group]
        )

        https_listener.add_target_groups(
            "JobsRule",
            priority=2,
            conditions=[
                elbv2.ListenerCondition.path_patterns([
                    "/proctorio/send-monthly-report",
                    "/set/active-campaign-tags",
                    "/sync/airtable-active-campaign",
                    "/script/*"
                ])
            ],
            target_groups=[self.jobs_target_group]
        )

        # Add tags
        cdk.Tags.of(self).add("bounded_context", "outlier")
        cdk.Tags.of(self).add("env", self.environment)

    @property
    def service_target_group(self) -> elbv2.IApplicationTargetGroup:
        return self.service_target_group

    @property
    def jobs_target_group(self) -> elbv2.IApplicationTargetGroup:
        return self.jobs_target_group