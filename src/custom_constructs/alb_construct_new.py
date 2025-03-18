import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
    Duration
)
from .base_construct import BaseConstruct


class AlbConstructNew(BaseConstruct):
    def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc, security_group: ec2.ISecurityGroup, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Load Balancer
        self._alb = elbv2.ApplicationLoadBalancer(
            self, "BlueGreenALB",
            vpc=vpc,
            internet_facing=True,
            security_group=security_group,
            load_balancer_name="outlier-blue-green"
        )

        # Import the hosted zone
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, "ExistingHostedZone",
            hosted_zone_id="Z05574991AFW5NGZ1X8DH",
            zone_name="nightly.savvasoutlier.com"
        )

        # Create an A record pointing to the ALB
        route53.ARecord(
            self, "ApiDnsRecord",
            zone=hosted_zone,
            record_name="api",  # This will create api.nightly.savvasoutlier.com
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(self._alb)
            )
        )

        # Import the SSL certificate
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate",
            "arn:aws:acm:us-east-1:528757783796:certificate/71eac7f3-f4f4-4a6c-a32b-d6dad41f94e8"
        )

        # Target Groups
        self._blue_target_group = elbv2.ApplicationTargetGroup(
            self, "BlueTargetGroup",
            vpc=vpc,
            port=1337,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        self._green_target_group = elbv2.ApplicationTargetGroup(
            self, "GreenTargetGroup",
            vpc=vpc,
            port=1337,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        # HTTPS Listener
        self._https_listener = self._alb.add_listener(
            "HttpsListener",
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[certificate],
            ssl_policy=elbv2.SslPolicy.RECOMMENDED,
            default_target_groups=[self._blue_target_group]
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

    @property
    def alb(self) -> elbv2.IApplicationLoadBalancer:
        return self._alb

    @property
    def blue_target_group(self) -> elbv2.IApplicationTargetGroup:
        return self._blue_target_group

    @property
    def green_target_group(self) -> elbv2.IApplicationTargetGroup:
        return self._green_target_group

    @property
    def https_listener(self) -> elbv2.IApplicationListener:
        return self._https_listener

    @property
    def http_listener(self) -> elbv2.IApplicationListener:
        return self._http_listener