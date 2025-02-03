import aws_cdk as cdk
from constructs import Construct
from custom_constructs.network_construct import NetworkConstruct


class BaseStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ↓↓ instantiate your constructs here ↓↓

        
        # Create network resources
        network = NetworkConstruct(self, "NetworkConstruct")

        # Store security groups for other resources to use later
        self.alb_sg = network.alb_security_group
        self.service_sg = network.service_security_group
        self.rds_sg = network.rds_security_group
        self.secrets_sg = network.secrets_manager_security_group