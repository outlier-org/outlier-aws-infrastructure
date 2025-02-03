import aws_cdk as cdk
from constructs import Construct
from custom_constructs.network_construct import NetworkConstruct
# from custom_constructs.database_construct import DatabaseConstruct
from custom_constructs.ecr_construct import EcrConstruct

class BaseStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ↓↓ instantiate constructs here ↓↓

        # Create network resources
        network = NetworkConstruct(self, "NetworkConstruct")

        # ECR repository
        ecr = EcrConstruct(self, "EcrConstruct")

        # Store security groups for other resources to use later
        self.alb_sg = network.alb_security_group
        self.service_sg = network.service_security_group
        self.rds_sg = network.rds_security_group
        self.secrets_sg = network.secrets_manager_security_group

        # Create outlier_nightly RDS database
        # database = DatabaseConstruct(
        #     self,
        #     "DatabaseConstruct",
        #     vpc=network.vpc,
        #     rds_security_groups=[network.rds_security_group]
        # )