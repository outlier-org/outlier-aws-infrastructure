# src/custom_constructs/alb_construct.py
from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
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

        # Create ALB
        self._alb = elbv2.ApplicationLoadBalancer(
            self,
            "ALB",
            vpc=vpc,
            internet_facing=True,
            security_group=security_group,
            load_balancer_name=f"outlier-alb-{self.environment}"
        )

        # Create main service target group
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

        # Main listener
        self._main_listener = self._alb.add_listener(
            "MainListener",
            port=80,
            default_target_groups=[self._main_target_group]
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

        # Add jobs listener rule
        self._main_listener.add_action(
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



# # src/custom_constructs/alb_construct.py
# from aws_cdk import aws_elasticloadbalancingv2 as elbv2
# from aws_cdk import aws_ec2 as ec2
# from aws_cdk import aws_certificatemanager as acm
# import aws_cdk as cdk
# from constructs import Construct
# from .base_construct import BaseConstruct
#
# class AlbConstruct(BaseConstruct):
#     def __init__(
#             self,
#             scope: Construct,
#             id: str,
#             vpc: ec2.IVpc,
#             security_group: ec2.ISecurityGroup,
#             subnets: list[ec2.ISubnet]
#     ):
#         super().__init__(scope, id)
#
#         # Import existing certificate
#         certificate = acm.Certificate.from_certificate_arn(
#             self,
#             "AlbCertificate",
#             "arn:aws:acm:us-east-1:528757783796:certificate/a9387ff3-5327-448e-b1a2-3ca8e3e1e7f4"
#         )
#
#         # Create ALB
#         self._load_balancer = elbv2.ApplicationLoadBalancer(
#             self,
#             "ApplicationLoadBalancer",
#             load_balancer_name=f"outlier-service-alb-{self.environment}-test",
#             vpc=vpc,
#             internet_facing=True,
#             security_group=security_group,
#             vpc_subnets=ec2.SubnetSelection(subnets=subnets),
#             idle_timeout=cdk.Duration.seconds(60),
#             http2_enabled=True,
#             deletion_protection=False
#         )
#
#         # Create Main Service Target Groups with optimized health checks
#         self._service_tg_1 = elbv2.ApplicationTargetGroup(
#             self,
#             "ServiceTargetGroup1",
#             target_group_name=f"out-main-tg-3-{self.environment}-test",
#             vpc=vpc,
#             port=1337,
#             protocol=elbv2.ApplicationProtocol.HTTP,
#             target_type=elbv2.TargetType.IP,
#             health_check=elbv2.HealthCheck(
#                 path="/",
#                 healthy_http_codes="200-499",
#                 interval=cdk.Duration.seconds(30),
#                 timeout=cdk.Duration.seconds(5),
#                 healthy_threshold_count=2,
#                 unhealthy_threshold_count=2,
#                 port="1337"
#             ),
#             deregistration_delay=cdk.Duration.seconds(30)  # Faster deregistration
#         )
#
#         self._service_tg_2 = elbv2.ApplicationTargetGroup(
#             self,
#             "ServiceTargetGroup2",
#             target_group_name=f"out-main-tg-4-{self.environment}-test",
#             vpc=vpc,
#             port=1337,
#             protocol=elbv2.ApplicationProtocol.HTTP,
#             target_type=elbv2.TargetType.IP,
#             health_check=elbv2.HealthCheck(
#                 path="/",
#                 healthy_http_codes="200-499",
#                 interval=cdk.Duration.seconds(30),
#                 timeout=cdk.Duration.seconds(5),
#                 healthy_threshold_count=2,
#                 unhealthy_threshold_count=2,
#                 port="1337"
#             ),
#             deregistration_delay=cdk.Duration.seconds(30)
#         )
#
#         # Create Jobs Service Target Groups with optimized health checks
#         self._jobs_tg_1 = elbv2.ApplicationTargetGroup(
#             self,
#             "JobsTargetGroup1",
#             target_group_name=f"out-jobs-tg-3-{self.environment}-test",
#             vpc=vpc,
#             port=1337,
#             protocol=elbv2.ApplicationProtocol.HTTP,
#             target_type=elbv2.TargetType.IP,
#             health_check=elbv2.HealthCheck(
#                 path="/",
#                 healthy_http_codes="200-499",
#                 interval=cdk.Duration.seconds(30),
#                 timeout=cdk.Duration.seconds(5),
#                 healthy_threshold_count=2,
#                 unhealthy_threshold_count=2,
#                 port="1337"
#             ),
#             deregistration_delay=cdk.Duration.seconds(30)
#         )
#
#         self._jobs_tg_2 = elbv2.ApplicationTargetGroup(
#             self,
#             "JobsTargetGroup2",
#             target_group_name=f"out-jobs-tg-4-{self.environment}-test",
#             vpc=vpc,
#             port=1337,
#             protocol=elbv2.ApplicationProtocol.HTTP,
#             target_type=elbv2.TargetType.IP,
#             health_check=elbv2.HealthCheck(
#                 path="/",
#                 healthy_http_codes="200-499",
#                 interval=cdk.Duration.seconds(30),
#                 timeout=cdk.Duration.seconds(5),
#                 healthy_threshold_count=2,
#                 unhealthy_threshold_count=2,
#                 port="1337"
#             ),
#             deregistration_delay=cdk.Duration.seconds(30)
#         )
#
#         # Add HTTP Listener (defaults to service tg 1)
#         self._http_listener = self._load_balancer.add_listener(
#             "HttpListener",
#             port=80,
#             default_target_groups=[self._service_tg_1]
#         )
#
#         # Add HTTPS Listener (production traffic)
#         self._prod_listener = self._load_balancer.add_listener(
#             "HttpsListener",
#             port=443,
#             certificates=[certificate],
#             default_target_groups=[self._service_tg_1]
#         )
#
#         # Add Test Listener (for blue/green test traffic)
#         self._test_listener = self._load_balancer.add_listener(
#             "TestListener",
#             port=8080,
#             protocol=elbv2.ApplicationProtocol.HTTP,
#             default_target_groups=[self._service_tg_1]
#         )
#
#         # Add production listener rules for jobs
#         self._prod_listener.add_target_groups(
#             "CronRule",
#             priority=1,
#             conditions=[
#                 elbv2.ListenerCondition.path_patterns([
#                     "/cron-script",
#                     "/cron-script/*",
#                     "/test-cron",
#                     "/test-cron/*"
#                 ])
#             ],
#             target_groups=[self._jobs_tg_1]
#         )
#
#         self._prod_listener.add_target_groups(
#             "JobsRule",
#             priority=2,
#             conditions=[
#                 elbv2.ListenerCondition.path_patterns([
#                     "/proctorio/send-monthly-report",
#                     "/set/active-campaign-tags",
#                     "/sync/airtable-active-campaign",
#                     "/script/*"
#                 ])
#             ],
#             target_groups=[self._jobs_tg_1]
#         )
#
#         # Add test listener rules for jobs (mirror production rules)
#         self._test_listener.add_target_groups(
#             "TestCronRule",
#             priority=1,
#             conditions=[
#                 elbv2.ListenerCondition.path_patterns([
#                     "/cron-script",
#                     "/cron-script/*",
#                     "/test-cron",
#                     "/test-cron/*"
#                 ])
#             ],
#             target_groups=[self._jobs_tg_1]
#         )
#
#         self._test_listener.add_target_groups(
#             "TestJobsRule",
#             priority=2,
#             conditions=[
#                 elbv2.ListenerCondition.path_patterns([
#                     "/proctorio/send-monthly-report",
#                     "/set/active-campaign-tags",
#                     "/sync/airtable-active-campaign",
#                     "/script/*"
#                 ])
#             ],
#             target_groups=[self._jobs_tg_1]
#         )
#
#         # Add tags
#         cdk.Tags.of(self).add("bounded_context", "outlier")
#         cdk.Tags.of(self).add("env", self.environment)
#
#     @property
#     def load_balancer(self) -> elbv2.IApplicationLoadBalancer:
#         return self._load_balancer
#
#     @property
#     def production_listener(self) -> elbv2.IApplicationListener:
#         return self._prod_listener
#
#     @property
#     def test_listener(self) -> elbv2.IApplicationListener:
#         return self._test_listener
#
#     @property
#     def service_tg_1(self) -> elbv2.IApplicationTargetGroup:
#         return self._service_tg_1
#
#     @property
#     def service_tg_2(self) -> elbv2.IApplicationTargetGroup:
#         return self._service_tg_2
#
#     @property
#     def jobs_tg_1(self) -> elbv2.IApplicationTargetGroup:
#         return self._jobs_tg_1
#
#     @property
#     def jobs_tg_2(self) -> elbv2.IApplicationTargetGroup:
#         return self._jobs_tg_2