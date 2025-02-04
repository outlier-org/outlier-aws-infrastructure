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
        self._load_balancer = elbv2.ApplicationLoadBalancer(
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

        # Create Main Service Target Groups - Updated port and health check
        self._service_tg_1 = elbv2.ApplicationTargetGroup(
            self,
            "ServiceTargetGroup1",
            target_group_name=f"out-main-tg-1-{self.environment}-test",
            vpc=vpc,
            port=80,  # Changed to match nginx port
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/",  # Changed to root path for nginx
                healthy_http_codes="200-499",
                interval=cdk.Duration.seconds(30),
                healthy_threshold_count=2,  # Added for faster stabilization
                unhealthy_threshold_count=2
            ),
            deregistration_delay=cdk.Duration.seconds(30)  # Reduced for faster updates
        )

        self._service_tg_2 = elbv2.ApplicationTargetGroup(
            self,
            "ServiceTargetGroup2",
            target_group_name=f"out-main-tg-2-{self.environment}-test",
            vpc=vpc,
            port=80,  # Changed to match nginx port
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/",  # Changed to root path for nginx
                healthy_http_codes="200-499",
                interval=cdk.Duration.seconds(30),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2
            ),
            deregistration_delay=cdk.Duration.seconds(30)
        )

        # Create Jobs Service Target Groups - Updated port and health check
        self._jobs_tg_1 = elbv2.ApplicationTargetGroup(
            self,
            "JobsTargetGroup1",
            target_group_name=f"out-jobs-tg-1-{self.environment}-test",
            vpc=vpc,
            port=80,  # Changed to match nginx port
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/",  # Changed to root path for nginx
                healthy_http_codes="200-499",
                interval=cdk.Duration.seconds(30),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2
            ),
            deregistration_delay=cdk.Duration.seconds(30)
        )

        self._jobs_tg_2 = elbv2.ApplicationTargetGroup(
            self,
            "JobsTargetGroup2",
            target_group_name=f"out-jobs-tg-2-{self.environment}-test",
            vpc=vpc,
            port=80,  # Changed to match nginx port
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/",  # Changed to root path for nginx
                healthy_http_codes="200-499",
                interval=cdk.Duration.seconds(30),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2
            ),
            deregistration_delay=cdk.Duration.seconds(30)
        )

        # Rest of the construct remains the same...
        http_listener = self._load_balancer.add_listener(
            "HttpListener",
            port=80,
            default_target_groups=[self._service_tg_1]
        )

        https_listener = self._load_balancer.add_listener(
            "HttpsListener",
            port=443,
            certificates=[certificate],
            default_target_groups=[self._service_tg_1]
        )

        # Add listener rules for jobs (using jobs tg 1 initially)
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
            target_groups=[self._jobs_tg_1]
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
            target_groups=[self._jobs_tg_1]
        )

        # Add tags
        cdk.Tags.of(self).add("bounded_context", "outlier")
        cdk.Tags.of(self).add("env", self.environment)

    @property
    def load_balancer(self) -> elbv2.IApplicationLoadBalancer:
        return self._load_balancer

    @property
    def service_tg_1(self) -> elbv2.IApplicationTargetGroup:
        return self._service_tg_1

    @property
    def service_tg_2(self) -> elbv2.IApplicationTargetGroup:
        return self._service_tg_2

    @property
    def jobs_tg_1(self) -> elbv2.IApplicationTargetGroup:
        return self._jobs_tg_1

    @property
    def jobs_tg_2(self) -> elbv2.IApplicationTargetGroup:
        return self._jobs_tg_2