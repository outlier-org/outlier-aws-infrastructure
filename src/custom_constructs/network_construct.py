# src/custom_constructs/network_construct.py
from aws_cdk import aws_ec2 as ec2
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct


class NetworkConstruct(BaseConstruct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        sub_environment: str = "",
        create_endpoints: bool = True,
        create_security_groups: bool = False,
    ):
        super().__init__(scope, id)

        # Store parameters
        self.sub_environment = sub_environment

        # Existing VPC
        self.vpc = ec2.Vpc.from_lookup(
            self, "ExistingVPC", vpc_id="vpc-00059e30c80aa84f2"
        )

        # Import existing RDS Security Group
        self.rds_sg = ec2.SecurityGroup.from_security_group_id(
            self,
            "ExistingRdsSecurityGroup",
            "sg-05fcdaf33c1d2a016",
            allow_all_outbound=True,
        )

        # Create security groups if needed (for app stacks)
        if create_security_groups:
            self.create_security_groups()

        # Create VPC endpoints if needed (for base stack)
        if create_endpoints:
            self.create_vpc_endpoints()

    def create_security_groups(self):
        """Create application security groups"""
        # ALB Security Group
        alb_name = f"outlier-alb-{self.environment}{self.sub_environment}-sg"
        self.alb_sg = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=self.vpc,
            security_group_name=alb_name,
            description=f"Security group for {self.environment}{self.sub_environment} ALB",
            allow_all_outbound=True,
        )

        # Allow HTTP and HTTPS from anywhere
        self.alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from anywhere",
        )
        self.alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from anywhere",
        )

        # Service Security Group
        service_name = f"outlier-service-{self.environment}{self.sub_environment}-sg"
        self.service_sg = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=self.vpc,
            security_group_name=service_name,
            description=f"Security group for {self.environment}{self.sub_environment} ECS Services",
            allow_all_outbound=True,
        )

        # Allow from ALB
        self.service_sg.add_ingress_rule(
            peer=self.alb_sg,
            connection=ec2.Port.tcp(1337),
            description="Allow inbound from ALB",
        )

        # Add RDS ingress rule
        self.rds_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.service_sg.security_group_id),
            connection=ec2.Port.tcp(5432),
            description=f"Allow PostgreSQL from {self.environment}{self.sub_environment} ECS service",
        )

        # Add admin EC2 ingress to RDS if this is in BaseStack
        if not self.sub_environment:
            self.rds_sg.add_ingress_rule(
                peer=ec2.Peer.security_group_id("sg-0ce94b9da62545a35"),
                connection=ec2.Port.tcp(5432),
                description="Allow PostgreSQL from nightly admin EC2",
            )

    def create_vpc_endpoints(self):
        """Create VPC Endpoints for AWS services"""
        # Create security group for endpoints
        secrets_name = f"secrets-manager-to-ecs-sg-{self.environment}{self.sub_environment}"
        self.secrets_sg = ec2.SecurityGroup(
            self,
            "SecretsManagerSecurityGroup",
            vpc=self.vpc,
            security_group_name=secrets_name,
            description=f"Security group for Secrets Manager VPC Endpoint - {self.environment}{self.sub_environment}",
            allow_all_outbound=True,
        )

        # Secrets Manager rules
        self.secrets_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from VPC CIDR",
        )

        # Interface Endpoints
        interface_endpoints = [
            ("SecretsManager", ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER),
            ("EcrApi", ec2.InterfaceVpcEndpointAwsService.ECR),
            ("EcrDkr", ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER),
            ("Logs", ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS),
        ]

        for name, service in interface_endpoints:
            self.vpc.add_interface_endpoint(
                f"{name}Endpoint",
                service=service,
                security_groups=[self.secrets_sg],
                subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                private_dns_enabled=True,
            )

    @property
    def alb_security_group(self) -> ec2.ISecurityGroup:
        if hasattr(self, 'alb_sg'):
            return self.alb_sg
        raise AttributeError("No ALB security group - was create_security_groups=True?")

    @property
    def service_security_group(self) -> ec2.ISecurityGroup:
        if hasattr(self, 'service_sg'):
            return self.service_sg
        raise AttributeError("No Service security group - was create_security_groups=True?")

    @property
    def rds_security_group(self) -> ec2.ISecurityGroup:
        return self.rds_sg

    @property
    def secrets_manager_security_group(self) -> ec2.ISecurityGroup:
        if hasattr(self, "secrets_sg"):
            return self.secrets_sg
        raise AttributeError("No secrets_sg defined - was create_endpoints=True?")