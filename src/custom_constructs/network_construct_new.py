import aws_cdk as cdk
from constructs import Construct
from aws_cdk import aws_ec2 as ec2
from .base_construct import BaseConstruct


class NetworkConstructNew(BaseConstruct):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Existing VPC
        self._vpc = ec2.Vpc.from_lookup(
            self, "ExistingVPC",
            vpc_id="vpc-00059e30c80aa84f2"
        )

        # Import existing RDS Security Group
        self._rds_security_group = ec2.SecurityGroup.from_security_group_id(
            self,
            "ExistingRdsSecurityGroup",
            "sg-05fcdaf33c1d2a016",
            allow_all_outbound=True
        )

        # Security Groups
        self._alb_security_group = ec2.SecurityGroup(
            self, "AlbSecurityGroup-BlueGreen",
            vpc=self._vpc,
            security_group_name=f"outlier-alb-bluegreen-{self.environment}-sg",
            description="Security group for Blue/Green ALB",
            allow_all_outbound=True
        )
        self._alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(80),
            "Allow HTTP from anywhere"
        )
        self._alb_security_group.add_ingress_rule(
            ec2.Peer.ipv4(self._vpc.vpc_cidr_block), ec2.Port.tcp(8080),
            "Allow test traffic from within VPC"
        )

        self._service_security_group = ec2.SecurityGroup(
            self, "ServiceSecurityGroup-BlueGreen",
            vpc=self._vpc,
            security_group_name=f"outlier-service-bluegreen-{self.environment}-sg",
            description="Security group for ECS Service",
            allow_all_outbound=True
        )
        self._service_security_group.add_ingress_rule(
            self._alb_security_group, ec2.Port.tcp(1337),
            "Allow from ALB"
        )

        # Add RDS ingress rule to allow access FROM our service security group
        self._rds_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self._service_security_group.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from ECS service"
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