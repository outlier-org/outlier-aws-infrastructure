from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_certificatemanager as acm,
    Duration
)
from constructs import Construct
from .base_construct import BaseConstruct

class AlbConstruct(BaseConstruct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            vpc: ec2.IVpc,
            security_group: ec2.ISecurityGroup
    ):
        super().__init__(scope, id)

        # Import existing certificate
        certificate = acm.Certificate.from_certificate_arn(
            self,
            "Certificate",
            "arn:aws:acm:us-east-1:528757783796:certificate/32cd5961-1a5d-4052-876a-0916d0c1c782"
        )

        # Create ALB (no changes)
        self._alb = elbv2.ApplicationLoadBalancer(
            self,
            "ALB",
            vpc=vpc,
            internet_facing=True,
            security_group=security_group,
            load_balancer_name=f"outlier-service-alb-{self.environment}"
        )

        # Create main service target group (no changes)
        self._main_target_group = elbv2.ApplicationTargetGroup(
            self,
            "MainServiceTargetGroup",
            vpc=vpc,
            port=1337,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        # HTTPS Listener (new)
        self._https_listener = self._alb.add_listener(
            "HttpsListener",
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[certificate],
            ssl_policy=elbv2.SslPolicy.RECOMMENDED,
            default_target_groups=[self._main_target_group]
        )

        # HTTP Listener (modified to redirect to HTTPS)
        self._http_listener = self._alb.add_listener(
            "HttpListener",
            port=80,
            default_action=elbv2.ListenerAction.redirect(
                port="443",
                protocol="HTTPS",
                permanent=True
            )
        )

        # Jobs service target group (no changes)
        self._jobs_target_group = elbv2.ApplicationTargetGroup(
            self,
            "JobsServiceTargetGroup",
            vpc=vpc,
            port=1337,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        # Add jobs listener rule to HTTPS listener
        self._https_listener.add_action(
            "JobsListenerRule",
            conditions=[
                elbv2.ListenerCondition.path_patterns(["/jobs/*"])
            ],
            priority=1,
            action=elbv2.ListenerAction.forward([self._jobs_target_group])
        )

    @property
    def alb(self) -> elbv2.IApplicationLoadBalancer:
        return self._alb

    @property
    def main_target_group(self) -> elbv2.IApplicationTargetGroup:
        return self._main_target_group

    @property
    def jobs_target_group(self) -> elbv2.IApplicationTargetGroup:
        return self._jobs_target_group