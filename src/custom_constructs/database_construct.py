from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class DatabaseConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc, rds_security_groups: list[ec2.ISecurityGroup]):
        super().__init__(scope, id)

        # Create subnet group first
        self.subnet_group = rds.SubnetGroup(
            self,
            "RdsSubnetGroup",
            vpc=vpc,
            subnet_group_name=f"outlier-{self.environment}-subnet-group-test",
            description=f"Subnet group for outlier {self.environment} RDS",
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        # Create RDS instance from snapshot
        self.db_instance = rds.DatabaseInstanceFromSnapshot(
            self,
            "RdsInstance",
            snapshot_identifier="rds:outlier-nightly-2025-01-26-06-28",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_12
            ),
            allocated_storage=125,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.LARGE
            ),
            vpc=vpc,
            subnet_group=self.subnet_group,
            security_groups=rds_security_groups,
            publicly_accessible=False,
            deletion_protection=False,
            auto_minor_version_upgrade=False
        )


        # Create RDS instance from scratch
#         self.db_instance = rds.DatabaseInstance(
#             self,
#             "RdsInstance",
#             # Basic Settings
#             instance_identifier=f"outlier-{self.environment}-test",
#             engine=rds.DatabaseInstanceEngine.postgres(
#                 version=rds.PostgresEngineVersion.VER_12
#             ),
#             instance_type=ec2.InstanceType.of(
#                 ec2.InstanceClass.BURSTABLE3,
#                 ec2.InstanceSize.LARGE
#             ),
#             database_name=f"outlier_{self.environment}",
#
#             # Network Settings
#             vpc=vpc,
#             subnet_group=self.subnet_group,
#             security_groups=rds_security_groups,
#             multi_az=False,
#             publicly_accessible=False,
#
#             # Storage Settings
#             storage_type=rds.StorageType.GP3,
#             allocated_storage=125,
#             storage_encrypted=True,
#
#             # Backup Settings
#             backup_retention=cdk.Duration.days(7),
#             preferred_backup_window="06:17-06:47",
#             preferred_maintenance_window="sun:06:51-sun:07:21",
#             auto_minor_version_upgrade=False,
#             delete_automated_backups=True,
#
#             # Monitoring Settings
#             enable_performance_insights=False,
#             cloudwatch_logs_exports=["postgresql", "upgrade"],
#             monitoring_interval=cdk.Duration.seconds(0),
#
#             # Other Settings
#             deletion_protection=False,
#             copy_tags_to_snapshot=False,
#             parameters={
#                 # Using default parameter group
#             },
#
#             # Credentials - We'll use Secrets Manager in production
#             credentials=rds.Credentials.from_generated_secret(
#                 username="postgres",
#                 secret_name=f"outlier-{self.environment}-db-credentials-test"
#             )
#         )

        # Add tags
        cdk.Tags.of(self.db_instance).add("env", self.environment)
        cdk.Tags.of(self.db_instance).add("bounded_context", "outlier")
        cdk.Tags.of(self.subnet_group).add("env", self.environment)
        cdk.Tags.of(self.subnet_group).add("bounded_context", "outlier")

    @property
    def db_endpoint(self) -> str:
        return self.db_instance.instance_endpoint.hostname

    @property
    def db_port(self) -> int:
        return self.db_instance.instance_endpoint.port

    @property
    def db_secret(self) -> rds.DatabaseSecret:
        return self.db_instance.secret