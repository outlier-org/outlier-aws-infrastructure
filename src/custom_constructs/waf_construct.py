# src/custom_constructs/waf_construct.py
from aws_cdk import (
    aws_wafv2 as wafv2,
    aws_elasticloadbalancingv2 as elbv2,
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

        self._web_acl = wafv2.CfnWebACL(
            self,
            "OutlierApiWaf",
            name=f"outlier-api-alb-waf-{self.environment}",
            description=f"WAF for outlier API ALB ({self.environment})",
            scope='REGIONAL',
            default_action=wafv2.CfnWebACL.DefaultActionProperty(
                allow={}
            ),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=f"outlier-api-alb-waf-{self.environment}",
                sampled_requests_enabled=True
            ),
            rules=[
                self._create_rule("AWS-AWSManagedRulesCommonRuleSet", 0),
                self._create_rule("AWS-AWSManagedRulesKnownBadInputsRuleSet", 1),
                self._create_rule("AWS-AWSManagedRulesSQLiRuleSet", 2),
                self._create_rule("AWS-AWSManagedRulesAmazonIpReputationList", 3)
            ]
        )

        # Create the association between WAF and ALB
        self._association = wafv2.CfnWebACLAssociation(
            self,
            "WafAlbAssociation",
            resource_arn=alb.load_balancer_arn,
            web_acl_arn=self._web_acl.attr_arn
        )

    def _create_rule(self, name: str, priority: int) -> wafv2.CfnWebACL.RuleProperty:
        return wafv2.CfnWebACL.RuleProperty(
            name=name,
            priority=priority,
            override_action=wafv2.CfnWebACL.OverrideActionProperty(
                count={}  # Start in count mode
            ),
            statement=wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name=name,
                    vendor_name='AWS'
                )
            ),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=f"{name}-{self.environment}",
                sampled_requests_enabled=True
            )
        )

    @property
    def web_acl(self) -> wafv2.CfnWebACL:
        return self._web_acl

    @property
    def association(self) -> wafv2.CfnWebACLAssociation:
        return self._association