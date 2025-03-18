# src/custom_constructs/network_construct_new.py
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import aws_ec2 as ec2
from .base_construct import BaseConstruct


class NetworkConstructNew(BaseConstruct):
    def __init__(self, scope: Construct, id: str, sub_environment: str = "", **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Use the sub_environment to distinguish resources
        self.sub_environment = sub_environment

        # Existing VPC
        self._vpc = ec2.Vpc.from_lookup(
            self, "ExistingVPC", vpc_id="vpc-00059e30c80aa84f2"
        )

        # Import existing RDS Security Group
        self._rds_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            "ExistingRdsSecurityGroup",
            "sg-05fcdaf33c1d2a016",
            allow_all_outbound=True,
        )

        # Security Groups - Match original exactly but with different names
        self._alb_security_group = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=self._vpc,
            security_group_name=f"outlier-alb-{self.environment}{self.sub_environment}-sg",
            description=f"Security group for {self.environment}{self.sub_environment} ALB",
            allow_all_outbound=True,
        )

        # Identical to original - allow HTTP from anywhere
        self._alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP from anywhere"
        )

        # Also add HTTPS since we're redirecting to it
        self._alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "Allow HTTPS from anywhere"
        )

        self._service_security_group = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=self._vpc,
            security_group_name=f"outlier-service-{self.environment}{self.sub_environment}--sg",
            description=f"Security group for {self.environment}{self.sub_environment} ECS Service",
            allow_all_outbound=True,
        )

        # Identical to original - allow 1337 from ALB
        self._service_security_group.add_ingress_rule(
            self._alb_security_group, ec2.Port.tcp(1337), "Allow from ALB"
        )

        # Add RDS ingress rule exactly as original did
        self._rds_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(
                self._service_security_group.security_group_id
            ),
            connection=ec2.Port.tcp(5432),
            description=f"Allow PostgreSQL from {self.environment}{self.sub_environment} ECS service",
        )

    @property
    def vpc(self) -> ec2.IVpc:
        return self._vpc

    @property
    def rds_security_group(self) -> ec2.ISecurityGroup:
        return self._rds_security_group

    @property
    def alb_security_group(self) -> ec2.ISecurityGroup:
        return self._alb_security_group

    @property
    def service_security_group(self) -> ec2.ISecurityGroup:
        return self._service_security_group
