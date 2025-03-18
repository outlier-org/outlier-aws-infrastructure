import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    Duration
)


class AlbConstruct(Construct):
    def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc,
                 security_group: ec2.ISecurityGroup, cert_arn: str,
                 hosted_zone_id: str, zone_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Load Balancer
        self.alb = elbv2.ApplicationLoadBalancer(
            self, "BlueGreenALB",
            vpc=vpc,
            internet_facing=True,
            security_group=security_group,
            load_balancer_name="outlier-blue-green"
        )

        # Import the SSL certificate
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate", cert_arn
        )

        # Target Groups
        self.blue_target_group = elbv2.ApplicationTargetGroup(
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

        self.green_target_group = elbv2.ApplicationTargetGroup(
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
        self.https_listener = self.alb.add_listener(
            "HttpsListener",
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[certificate],
            ssl_policy=elbv2.SslPolicy.RECOMMENDED,
            default_target_groups=[self.blue_target_group]
        )

        # HTTP Listener (redirects to HTTPS)
        self.http_listener = self.alb.add_listener(
            "HttpListener",
            port=80,
            default_action=elbv2.ListenerAction.redirect(
                port="443",
                protocol="HTTPS",
                permanent=True
            )
        )

        # DNS configuration
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self, "ExistingHostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=zone_name
        )

        # Create an A record pointing to the ALB
        route53.ARecord(
            self, "ApiDnsRecord",
            zone=hosted_zone,
            record_name="api",  # This will create api.nightly.savvasoutlier.com
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(self.alb)
            )
        )