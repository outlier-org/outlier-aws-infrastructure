# src/custom_constructs/waf_construct.py
from aws_cdk import (
    aws_wafv2 as wafv2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
)
from constructs import Construct
from .base_construct import BaseConstruct

class WafConstruct(BaseConstruct):
    def __init__(
            self,
            scope: Construct,
            id: str,
            alb: elbv2.IApplicationLoadBalancer
    ):
        super().__init__(scope, id)

        # Create CloudWatch Log Group for WAF
        self._log_group = logs.LogGroup(
            self,
            "WafLogGroup",
            log_group_name=f"aws-waf-logs-{self.environment}",
            retention=logs.RetentionDays.ONE_MONTH
        )

        # Create WAF ACL with all four rules
        self._web_acl = wafv2.CfnWebACL(
            self,
            "OutlierApiWaf",
            name=f"outlier-api-waf-{self.environment}",
            description="WAF for Outlier API",
            scope='REGIONAL',
            default_action=wafv2.CfnWebACL.DefaultActionProperty(
                allow={}
            ),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=f"outlier-api-waf-{self.environment}",
                sampled_requests_enabled=True
            ),
            rules=[
                {
                    "name": "CommonRuleSet",
                    "priority": 0,
                    "override_action": {
                        "count": {}
                    },
                    "statement": {
                        "managedRuleGroupStatement": {
                            "vendorName": "AWS",
                            "name": "AWSManagedRulesCommonRuleSet"
                        }
                    },
                    "visibility_config": {
                        "sampledRequestsEnabled": True,
                        "cloudWatchMetricsEnabled": True,
                        "metricName": "CommonRuleSetMetric"
                    }
                },
                {
                    "name": "KnownBadInputs",
                    "priority": 1,
                    "override_action": {
                        "count": {}
                    },
                    "statement": {
                        "managedRuleGroupStatement": {
                            "vendorName": "AWS",
                            "name": "AWSManagedRulesKnownBadInputsRuleSet"
                        }
                    },
                    "visibility_config": {
                        "sampledRequestsEnabled": True,
                        "cloudWatchMetricsEnabled": True,
                        "metricName": "KnownBadInputsMetric"
                    }
                },
                {
                    "name": "SQLiRules",
                    "priority": 2,
                    "override_action": {
                        "count": {}
                    },
                    "statement": {
                        "managedRuleGroupStatement": {
                            "vendorName": "AWS",
                            "name": "AWSManagedRulesSQLiRuleSet"
                        }
                    },
                    "visibility_config": {
                        "sampledRequestsEnabled": True,
                        "cloudWatchMetricsEnabled": True,
                        "metricName": "SQLiRulesMetric"
                    }
                },
                {
                    "name": "IPReputationList",
                    "priority": 3,
                    "override_action": {
                        "count": {}
                    },
                    "statement": {
                        "managedRuleGroupStatement": {
                            "vendorName": "AWS",
                            "name": "AWSManagedRulesAmazonIpReputationList"
                        }
                    },
                    "visibility_config": {
                        "sampledRequestsEnabled": True,
                        "cloudWatchMetricsEnabled": True,
                        "metricName": "IPReputationListMetric"
                    }
                }
            ]
        )

        # Enable logging for WAF
        self._logging = wafv2.CfnLoggingConfiguration(
            self,
            "WafLogging",
            log_destination_configs=[
                self._log_group.log_group_arn
            ],
            resource_arn=self._web_acl.attr_arn
        )

        # Associate with ALB
        self._association = wafv2.CfnWebACLAssociation(
            self,
            "WafAlbAssociation",
            resource_arn=alb.load_balancer_arn,
            web_acl_arn=self._web_acl.attr_arn
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