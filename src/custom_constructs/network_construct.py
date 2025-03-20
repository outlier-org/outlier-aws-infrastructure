from aws_cdk import aws_ec2 as ec2
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

"""
Network Construct that manages VPC resources, security groups, and VPC endpoints.
Supports both application and base infrastructure configurations.
"""


class NetworkConstruct(BaseConstruct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        sub_environment: str = "",
        create_endpoints: bool = True,
        create_application_security_groups: bool = False,
    ):
        super().__init__(scope, id)
        self.sub_environment = sub_environment

        # Import existing VPC by ID
        self.vpc = ec2.Vpc.from_lookup(
            self, "ExistingVPC", vpc_id="vpc-00059e30c80aa84f2"
        )

        # Initialize optional security groups and endpoints
        if create_application_security_groups:
            self.create_application_security_groups()

        if create_endpoints:
            self.create_vpc_endpoints()

    def create_application_security_groups(self):
        """
        Creates and configures security groups for RDS, ALB, and ECS services.
        Sets up ingress/egress rules for secure communication between components.
        """
        # Configure RDS security group
        self.rds_sg = ec2.SecurityGroup(
            self,
            "RdsSecurityGroup",
            vpc=self.vpc,
            security_group_name=f"outlier-rds-{self.environment}-sg-cdk",
            description=f"Security group for outlier {self.environment} RDS instance",
            allow_all_outbound=True,
        )

        # Configure ALB security group
        self.alb_sg = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=self.vpc,
            security_group_name=f"outlier-alb-{self.environment}{self.sub_environment}-sg-cdk",
            description=f"Security group for {self.environment}{self.sub_environment} ALB",
            allow_all_outbound=True,
        )

        # Configure service security group
        self.service_sg = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=self.vpc,
            security_group_name=f"outlier-service-{self.environment}{self.sub_environment}-sg-cdk",
            description=f"Security group for {self.environment}{self.sub_environment} ECS Services",
            allow_all_outbound=True,
        )

        # Define ingress rules for ALB
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

        # Define ingress rules for service
        self.service_sg.add_ingress_rule(
            peer=self.alb_sg,
            connection=ec2.Port.tcp(1337),
            description="Allow inbound from ALB",
        )

        # Define ingress rules for RDS
        self.rds_sg.add_ingress_rule(
            peer=self.service_sg,
            connection=ec2.Port.tcp(5432),
            description=f"Allow PostgreSQL from {self.environment}{self.sub_environment} ECS service",
        )

        self.rds_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id("sg-0ce94b9da62545a35"),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from nightly admin EC2",
        )

    def create_vpc_endpoints(self):
        """
        Creates VPC endpoints for AWS services (ECR, Secrets Manager, CloudWatch).
        Enables private communication between VPC resources and AWS services.
        """
        # Configure security group for VPC endpoints
        self.secrets_sg = ec2.SecurityGroup(
            self,
            "SecretsManagerSecurityGroup",
            vpc=self.vpc,
            security_group_name=f"secrets-manager-to-ecs-sg-{self.environment}{self.sub_environment}-v3",
            description=f"Security group for Secrets Manager VPC Endpoint - {self.environment}{self.sub_environment}",
            allow_all_outbound=True,
        )

        self.secrets_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from VPC CIDR",
        )

        # Create interface endpoints for AWS services
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
        if hasattr(self, "alb_sg"):
            return self.alb_sg
        raise AttributeError("No ALB security group - was create_security_groups=True?")

    @property
    def service_security_group(self) -> ec2.ISecurityGroup:
        if hasattr(self, "service_sg"):
            return self.service_sg
        raise AttributeError(
            "No Service security group - was create_security_groups=True?"
        )

    @property
    def rds_security_group(self) -> ec2.ISecurityGroup:
        return self.rds_sg

    @property
    def secrets_manager_security_group(self) -> ec2.ISecurityGroup:
        if hasattr(self, "secrets_sg"):
            return self.secrets_sg
        raise AttributeError("No secrets_sg defined - was create_endpoints=True?")
