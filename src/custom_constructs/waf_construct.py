from aws_cdk import (
    aws_wafv2 as wafv2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    RemovalPolicy,
)
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

"""
WAF Construct that manages Web Application Firewall configuration and logging.
Implements AWS managed rule sets for common attacks, SQL injection, and IP reputation filtering.
"""


class WafConstruct(BaseConstruct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        alb: elbv2.IApplicationLoadBalancer,
        sub_environment: str = "",
    ):
        super().__init__(scope, id)

        # Configure WAF logging to CloudWatch
        self._log_group = logs.LogGroup(
            self,
            "WafLogGroup",
            log_group_name=f"aws-waf-logs-{self.environment}{sub_environment}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # Create WAF Web ACL with managed rule sets
        self._web_acl = wafv2.CfnWebACL(
            self,
            "OutlierApiWaf",
            name=f"outlier-api-waf-{self.environment}{sub_environment}",
            description="WAF for Outlier API",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=f"outlier-api-waf-{self.environment}{sub_environment}",
                sampled_requests_enabled=True,
            ),
            rules=[
                # AWS Common Rule Set - basic attack patterns
                wafv2.CfnWebACL.RuleProperty(
                    name="CommonRuleSet",
                    priority=0,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(count={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS", name="AWSManagedRulesCommonRuleSet"
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="CommonRuleSetMetric",
                    ),
                ),
                # Known Bad Inputs Rule Set - malicious request patterns
                wafv2.CfnWebACL.RuleProperty(
                    name="KnownBadInputs",
                    priority=1,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(count={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesKnownBadInputsRuleSet",
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="KnownBadInputsMetric",
                    ),
                ),
                # SQL Injection Rule Set - SQL attack prevention
                wafv2.CfnWebACL.RuleProperty(
                    name="SQLiRules",
                    priority=2,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(count={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS", name="AWSManagedRulesSQLiRuleSet"
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="SQLiRulesMetric",
                    ),
                ),
                # IP Reputation List - known malicious IP addresses
                wafv2.CfnWebACL.RuleProperty(
                    name="IPReputationList",
                    priority=3,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(count={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesAmazonIpReputationList",
                        )
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="IPReputationListMetric",
                    ),
                ),
            ],
        )

        # Enable WAF logging to CloudWatch
        self._logging = wafv2.CfnLoggingConfiguration(
            self,
            "WafLogging",
            log_destination_configs=[self._log_group.log_group_arn],
            resource_arn=self._web_acl.attr_arn,
        )

        # Associate WAF with Application Load Balancer
        self._association = wafv2.CfnWebACLAssociation(
            self,
            "WafAlbAssociation",
            resource_arn=alb.load_balancer_arn,
            web_acl_arn=self._web_acl.attr_arn,
        )

    @property
    def web_acl(self) -> wafv2.CfnWebACL:
        return self._web_acl

    @property
    def log_group(self) -> logs.ILogGroup:
        return self._log_group

    @property
    def association(self) -> wafv2.CfnWebACLAssociation:
        return self._association
