from aws_cdk import aws_ec2 as ec2
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class NetworkConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        self.vpc = ec2.Vpc.from_lookup(
            self,
            "ExistingVPC",
            vpc_id="vpc-00059e30c80aa84f2"
        )

        self.create_security_groups()
        self.create_vpc_endpoints()

    def create_security_groups(self):
        """Create all application security groups"""
        # ALB Security Group
        alb_name = f"outlier-alb-{self.environment}-sg-test"
        self.alb_sg = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=self.vpc,
            security_group_name=alb_name,
            description=f"Security group for Outlier ALB - {self.environment}",
            allow_all_outbound=True
        )

        # Service Security Group
        service_name = f"outlier-service-{self.environment}-sg-test"
        self.service_sg = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=self.vpc,
            security_group_name=service_name,
            description=f"Security group for Outlier Services - {self.environment}",
            allow_all_outbound=True
        )

        # RDS Security Group
        rds_name = f"outlier-rds-{self.environment}-sg-test"
        self.rds_sg = ec2.SecurityGroup(
            self,
            "RdsSecurityGroup",
            vpc=self.vpc,
            security_group_name=rds_name,
            description=f"Security group for outlier {self.environment} RDS instance",
            allow_all_outbound=True
        )

        # Secrets Manager Endpoint Security Group
        secrets_name = f"secrets-manager-to-ecs-sg-{self.environment}-test"
        self.secrets_sg = ec2.SecurityGroup(
            self,
            "SecretsManagerSecurityGroup",
            vpc=self.vpc,
            security_group_name=secrets_name,
            description=f"Security group for Secrets Manager VPC Endpoint - {self.environment}",
            allow_all_outbound=True
        )

        # Add ingress rules

        # ALB rules
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

        # Add standard tags using the variables we stored
        sg_names = {
            self.alb_sg: alb_name,
            self.service_sg: service_name,
            self.rds_sg: rds_name,
            self.secrets_sg: secrets_name
        }

    def create_vpc_endpoints(self):
        """Create VPC Endpoints for AWS services"""

        # Gateway Endpoints
        self.s3_gateway_endpoint = self.vpc.add_gateway_endpoint(
            "S3GatewayEndpoint-test",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)]
        )

        self.dynamodb_endpoint = self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint-test",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)]
        )

        # Interface Endpoints
        interface_endpoints = [
            ("SecretsManager", ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER),
            ("EcrApi", ec2.InterfaceVpcEndpointAwsService.ECR),
            ("EcrDkr", ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER),
            ("Logs", ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS)
        ]

        for name, service in interface_endpoints:
            self.vpc.add_interface_endpoint(
                f"{name}Endpoint-test",
                service=service,
                security_groups=[self.service_sg],
                subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                private_dns_enabled=True
            )

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