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

        # Create WAF using L1 construct (direct CloudFormation mapping)
        self._web_acl = wafv2.CfnWebACL(
            self,
            "OutlierApiWaf",
            name=f"outlier-api-waf-{self.environment}",
            description="WAF for Outlier API",
            scope="REGIONAL",
            default_action={
                "allow": {}
            },
            visibility_config={
                "cloudWatchMetricsEnabled": True,
                "metricName": f"outlier-api-waf-{self.environment}",
                "sampledRequestsEnabled": True
            },
            rules=[
                {
                    "name": "AWSManagedRulesCommonRuleSet",
                    "priority": 0,
                    "overrideAction": {
                        "count": {}
                    },
                    "statement": {
                        "managedRuleGroupStatement": {
                            "vendorName": "AWS",
                            "name": "AWSManagedRulesCommonRuleSet"
                        }
                    },
                    "visibilityConfig": {
                        "cloudWatchMetricsEnabled": True,
                        "metricName": "AWSManagedRulesCommonRuleSetMetric",
                        "sampledRequestsEnabled": True
                    }
                }
            ]
        )

        # Create association
        self._association = wafv2.CfnWebACLAssociation(
            self,
            "WafAlbAssociation",
            resource_arn=alb.load_balancer_arn,
            web_acl_arn=self._web_acl.attr_arn
        )

    @property
    def web_acl(self) -> wafv2.CfnWebACL:
        return self._web_acl