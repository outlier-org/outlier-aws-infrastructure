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
        # S3 Gateway Endpoint
        self.s3_gateway_endpoint = ec2.CfnVPCEndpoint(
            self,
            "S3GatewayEndpoint-nightly",
            vpc_endpoint_type="Gateway",
            vpc_id=self.vpc.vpc_id,
            service_name="com.amazonaws.us-east-1.s3",
            policy_document="{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"*\",\"Resource\":\"*\"}]}",
            route_table_ids=[rt.route_table_id for rt in self.vpc.private_route_tables],
            private_dns_enabled=False
        )

        # DynamoDB Gateway Endpoint
        self.dynamodb_endpoint = ec2.CfnVPCEndpoint(
            self,
            "DynamoDBEndpoint-nightly",
            vpc_endpoint_type="Gateway",
            vpc_id=self.vpc.vpc_id,
            service_name="com.amazonaws.us-east-1.dynamodb",
            policy_document="{\"Version\":\"2008-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"*\",\"Resource\":\"*\"}]}",
            route_table_ids=[rt.route_table_id for rt in self.vpc.private_route_tables],
            private_dns_enabled=False
        )

        # Secrets Manager Interface Endpoint
        self.secrets_endpoint = ec2.CfnVPCEndpoint(
            self,
            "SecretsManagerEndpoint-nightly",
            vpc_endpoint_type="Interface",
            vpc_id=self.vpc.vpc_id,
            service_name="com.amazonaws.us-east-1.secretsmanager",
            policy_document='''{"Statement":[{"Action":"*","Effect":"Allow","Principal":"*","Resource":"*"}]}''',
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets],
            private_dns_enabled=True,
            security_group_ids=[self.service_sg.security_group_id]
        )

        # ECR API Interface Endpoint
        self.ecr_api_endpoint = ec2.CfnVPCEndpoint(
            self,
            "EcrApiEndpoint-nightly",
            vpc_endpoint_type="Interface",
            vpc_id=self.vpc.vpc_id,
            service_name="com.amazonaws.us-east-1.ecr.api",
            policy_document='''{"Statement":[{"Action":"*","Effect":"Allow","Principal":"*","Resource":"*"}]}''',
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets],
            private_dns_enabled=True,
            security_group_ids=[self.service_sg.security_group_id]
        )

        # ECR Docker Interface Endpoint
        self.ecr_dkr_endpoint = ec2.CfnVPCEndpoint(
            self,
            "EcrDkrEndpoint-nightly",
            vpc_endpoint_type="Interface",
            vpc_id=self.vpc.vpc_id,
            service_name="com.amazonaws.us-east-1.ecr.dkr",
            policy_document='''{"Statement":[{"Action":"*","Effect":"Allow","Principal":"*","Resource":"*"}]}''',
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets],
            private_dns_enabled=True,
            security_group_ids=[self.service_sg.security_group_id]
        )

        # CloudWatch Logs Interface Endpoint
        self.logs_endpoint = ec2.CfnVPCEndpoint(
            self,
            "CloudWatchLogsEndpoint-nightly",
            vpc_endpoint_type="Interface",
            vpc_id=self.vpc.vpc_id,
            service_name="com.amazonaws.us-east-1.logs",
            policy_document='''{"Statement":[{"Action":"*","Effect":"Allow","Principal":"*","Resource":"*"}]}''',
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets],
            private_dns_enabled=True,
            security_group_ids=[self.service_sg.security_group_id]
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