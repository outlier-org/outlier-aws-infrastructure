from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
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

        # First create the ALB
        self._alb = elbv2.ApplicationLoadBalancer(
            self,
            "ALB",
            vpc=vpc,
            internet_facing=True,
            security_group=security_group,
            load_balancer_name=f"outlier-service-alb-{self.environment}"
        )

        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self,
            "ExistingHostedZone",
            hosted_zone_id="Z05574991AFW5NGZ1X8DH",
            zone_name="nightly.savvasoutlier.com"
        )

        # Create A record (CDK managed)
        route53.ARecord(
            self,
            "ApiDnsRecord",
            zone=hosted_zone,
            record_name="api3",  # This will create api.nightly.savvasoutlier.com
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(self._alb)
            )
        )

        # Import certificate (verify it covers *.nightly.savvasoutlier.com)
        certificate = acm.Certificate.from_certificate_arn(
            self,
            "Certificate",
            "arn:aws:acm:us-east-1:528757783796:certificate/71eac7f3-f4f4-4a6c-a32b-d6dad41f94e8"
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

        # HTTP Listener (redirects to HTTPS)
        self._http_listener = self._alb.add_listener(
            "HttpListener",
            port=80,
            default_action=elbv2.ListenerAction.redirect(
                port="443",
                protocol="HTTPS",
                permanent=True
            )
        )

        # Jobs service target group
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

        # Jobs listener rule on HTTPS listener
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