import aws_cdk as cdk
from constructs import Construct
from aws_cdk import aws_ec2 as ec2


class NetworkConstruct(Construct):
    def __init__(self, scope: Construct, id: str, vpc_id: str, rds_sg_id: str, environment: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Existing VPC
        self.vpc = ec2.Vpc.from_lookup(
            self, "ExistingVPC",
            vpc_id=vpc_id
        )

        # Import existing RDS Security Group
        self.rds_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            "ExistingRdsSecurityGroup",
            rds_sg_id,
            allow_all_outbound=True
        )

        # ALB Security Group
        self.alb_security_group = ec2.SecurityGroup(
            self, "AlbSecurityGroup-BlueGreen",
            vpc=self.vpc,
            security_group_name=f"outlier-alb-bluegreen-{environment}-sg",
            description="Security group for Blue/Green ALB",
            allow_all_outbound=True
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(80),
            "Allow HTTP from anywhere"
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(443),
            "Allow HTTPS from anywhere"
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.tcp(8080),
            "Allow test traffic from within VPC"
        )

        # Service Security Group
        self.service_security_group = ec2.SecurityGroup(
            self, "ServiceSecurityGroup-BlueGreen",
            vpc=self.vpc,
            security_group_name=f"outlier-service-bluegreen-{environment}-sg",
            description="Security group for ECS Service",
            allow_all_outbound=True
        )
        self.service_security_group.add_ingress_rule(
            self.alb_security_group, ec2.Port.tcp(1337),
            "Allow from ALB"
        )

        # Add RDS ingress rule
        self.rds_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.service_security_group.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from ECS service"
        )