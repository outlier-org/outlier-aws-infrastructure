# src/custom_constructs/database_construct.py - With version fix
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct

class DatabaseConstruct(BaseConstruct):
    def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc, security_group: ec2.ISecurityGroup):
        super().__init__(scope, id)

        # Define PostgreSQL 16.4 version manually since it might not be in CDK enum yet
        pg_engine_version = rds.AuroraPostgresEngineVersion.of("16.4", "16")

        # Create custom cluster parameter group with Zero-ETL settings
        cluster_param_group = rds.ParameterGroup(
            self,
            "CustomClusterParamGroup",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=pg_engine_version),
            description="Contains unique parameters for: Zero-ETL, PSQL slow-query-logging",
            parameters={
                "aurora.enhanced_logical_replication": "1",
                "aurora.logical_replication_backup": "0",
                "aurora.logical_replication_globaldb": "0",
                "rds.logical_replication": "1"
            }
        )

        # Create custom instance parameter group with slow query logging settings
        instance_param_group = rds.ParameterGroup(
            self,
            "CustomInstanceParamGroup",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=pg_engine_version),
            description="Contains unique parameters for: PSQL slow-query-logging",
            parameters={
                "auto_explain.log_analyze": "1",
                "auto_explain.log_format": "json",
                "auto_explain.log_min_duration": "200",
                "log_min_duration_statement": "200",
                "shared_preload_libraries": "pg_stat_statements,auto_explain"
            }
        )

        # Create the Aurora cluster from snapshot with custom parameter groups
        self.db_cluster = rds.DatabaseClusterFromSnapshot(
            self,
            "NightlyDBCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=pg_engine_version),
            instances=2,
            instance_props=rds.InstanceProps(
                vpc=vpc,
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.R7G,
                    ec2.InstanceSize.LARGE
                ),
                security_groups=[security_group],
                parameter_group=instance_param_group,
                enable_performance_insights=False,
                publicly_accessible=False,
            ),
            snapshot_identifier="rds:outlier-nightly-db-cluster-2025-03-11-03-37",
            cluster_identifier="outlier-nightly-db-cluster",
            port=5432,
            instance_identifier_base="outlier-nightly-db",
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                availability_zones=["us-east-1b", "us-east-1c"]
            ),
            storage_encrypted=True,
            deletion_protection=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            parameter_group=cluster_param_group,
            cloudwatch_logs_exports=["postgresql"]
        )

    @property
    def cluster_endpoint(self) -> str:
        return self.db_cluster.cluster_endpoint.hostname

    @property
    def reader_endpoint(self) -> str:
        return self.db_cluster.cluster_read_endpoint.hostname

    @property
    def db_port(self) -> int:
        return self.db_cluster.cluster_endpoint.port
