import aws_cdk as cdk
from constructs import Construct
from custom_constructs.network_construct import NetworkConstruct
from custom_constructs.iam_construct import IamConstruct


class BaseStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Network resources
        network = NetworkConstruct(
            self,
            "NetworkConstruct",
            create_endpoints=True,
            create_application_security_groups=False,
        )

        # IAM resources
        iam = IamConstruct(self, "IamConstruct")
