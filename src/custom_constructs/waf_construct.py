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

        # Create basic WAF first
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
                # Start with just one rule to test
                self._create_common_rule_set()
            ]
        )

        # Associate with ALB
        self._association = wafv2.CfnWebACLAssociation(
            self,
            "WafAlbAssociation",
            resource_arn=alb.load_balancer_arn,
            web_acl_arn=self._web_acl.attr_arn
        )

    def _create_common_rule_set(self) -> wafv2.CfnWebACL.RuleProperty:
        return wafv2.CfnWebACL.RuleProperty(
            name="AWS-AWSManagedRulesCommonRuleSet",
            priority=0,
            override_action=wafv2.CfnWebACL.OverrideActionProperty(
                count={}
            ),
            statement=wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    vendor_name="AWS",
                    name="AWSManagedRulesCommonRuleSet"
                )
            ),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="AWS-AWSManagedRulesCommonRuleSet",
                sampled_requests_enabled=True
            )
        )

    @property
    def web_acl(self) -> wafv2.CfnWebACL:
        return self._web_acl