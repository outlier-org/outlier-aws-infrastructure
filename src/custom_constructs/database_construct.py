from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class DatabaseConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc, rds_security_groups: list[ec2.ISecurityGroup]):
        super().__init__(scope, id)

        # Create subnet group first - exact match
        self.subnet_group = rds.CfnDBSubnetGroup(
            self,
            "RdsSubnetGroup",
            db_subnet_group_description="Subnet group for outlier nightly RDS",
            db_subnet_group_name="outlier-nightly-subnet-group",
            subnet_ids=[
                "subnet-0a92401d83e646775",
                "subnet-031293b41be863713",
                "subnet-0105fa1e5a7b370c4"
            ]
        )

        # Create RDS instance - exact match
        self.db_instance = rds.CfnDBInstance(
            self,
            "RdsInstance",
            db_instance_identifier="outlier-nightly",
            allocated_storage=125,
            db_instance_class="db.t3.large",
            engine="postgres",
            master_username="postgres",
            master_user_password="REPLACEME",  # You'll want to handle this securely
            db_name="outlier_nightly",
            preferred_backup_window="06:17-06:47",
            backup_retention_period=7,
            availability_zone=vpc.availability_zones[0],  # Matches your AZ
            preferred_maintenance_window="sun:06:51-sun:07:21",
            multi_az=False,
            engine_version="12.20",
            auto_minor_version_upgrade=False,
            license_model="postgresql-license",
            iops=3000,
            publicly_accessible=False,
            storage_type="gp3",
            port=5432,
            storage_encrypted=False,
            copy_tags_to_snapshot=False,
            monitoring_interval=0,
            enable_iam_database_authentication=False,
            enable_performance_insights=False,
            deletion_protection=False,
            db_subnet_group_name=self.subnet_group.db_subnet_group_name,
            vpc_security_groups=[sg.security_group_id for sg in rds_security_groups],
            db_parameter_group_name="default.postgres12",
            option_group_name="default:postgres-12",
            enable_cloudwatch_logs_exports=[
                "postgresql",
                "upgrade"
            ],
            ca_certificate_identifier="rds-ca-rsa2048-g1",
            tags=[
                {
                    "key": "bounded_context",
                    "value": "outlier"
                },
                {
                    "key": "env",
                    "value": self.environment
                }
            ]
        )

    @property
    def db_endpoint(self) -> str:
        return f"{self.db_instance.ref}.{self.region}.rds.amazonaws.com"

    @property
    def db_port(self) -> int:
        return 5432

    @property
    def db_secret(self) -> rds.DatabaseSecret:
        return self.db_instance.secret