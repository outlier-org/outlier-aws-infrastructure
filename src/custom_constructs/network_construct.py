from aws_cdk import aws_ec2 as ec2
from constructs import Construct
from .base_construct import BaseConstruct

class NetworkConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # Reference specific VPC by ID
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "ExistingVPC",
            vpc_id="vpc-00059e30c80aa84f2"  # vpc_nightly_outlier
        )

        # Create all security groups
        self.create_security_groups()

    def create_security_groups(self):
        """Create all application security groups"""

        # ALB Security Group
        self.alb_sg = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=self.vpc,
            security_group_name=f"outlier-alb-{self.environment}-sg-cdk-test",
            description=f"Security group for Outlier ALB - {self.environment}",
            allow_all_outbound=True
        )

        # Service Security Group
        self.service_sg = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=self.vpc,
            security_group_name=f"outlier-service-{self.environment}-sg-cdk-test",
            description=f"Security group for Outlier Services - {self.environment}",
            allow_all_outbound=True
        )

        # RDS Security Group
        self.rds_sg = ec2.SecurityGroup(
            self,
            "RdsSecurityGroup",
            vpc=self.vpc,
            security_group_name=f"outlier-rds-{self.environment}-sg-cdk-test",
            description=f"Security group for outlier {self.environment} RDS instance",
            allow_all_outbound=True
        )

        # Secrets Manager Endpoint Security Group
        self.secrets_sg = ec2.SecurityGroup(
            self,
            "SecretsManagerSecurityGroup",
            vpc=self.vpc,
            security_group_name=f"secrets-manager-to-ecs-sg-{self.environment}-cdk-test",
            description=f"Security group for Secrets Manager VPC Endpoint - {self.environment}",
            allow_all_outbound=True
        )

        # ALB ingress rules
        self.alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from anywhere"
        )
        self.alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from anywhere"
        )

        # ALB egress rules
        self.alb_sg.add_egress_rule(
            peer=ec2.Peer.security_group_id(self.service_sg.security_group_id),
            connection=ec2.Port.tcp(80),
            description="Allow outbound to targets"
        )

        # Service rules
        self.service_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.alb_sg.security_group_id),
            connection=ec2.Port.tcp(80),
            description="Allow inbound from ALB"
        )

        # RDS rules
        self.rds_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.service_sg.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from ECS service"
        )
        # Add ingress from admin EC2
        self.rds_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id("sg-0ce94b9da62545a35"),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from nightly admin EC2"
        )

        # Secrets Manager rules
        self.secrets_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.service_sg.security_group_id),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from ECS service"
        )

        # Add standard tags
        for sg in [self.alb_sg, self.service_sg, self.rds_sg, self.secrets_sg]:
            ec2.Tags.of(sg).add("env", self.environment)
            ec2.Tags.of(sg).add("bounded_context", "outlier")
            ec2.Tags.of(sg).add("Name", sg.security_group_name)

    @property
    def alb_security_group(self) -> ec2.ISecurityGroup:
        return self.alb_sg

    @property
    def service_security_group(self) -> ec2.ISecurityGroup:
        return self.service_sg

    @property
    def rds_security_group(self) -> ec2.ISecurityGroup:
        return self.rds_sg

    @property
    def secrets_manager_security_group(self) -> ec2.ISecurityGroup:
        return self.secrets_sg