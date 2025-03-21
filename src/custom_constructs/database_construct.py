from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
import aws_cdk as cdk
from constructs import Construct
from .base_construct import BaseConstruct


class DatabaseConstruct(BaseConstruct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.IVpc,
        security_group: ec2.ISecurityGroup,
    ):
        super().__init__(scope, id)

        # Define PostgreSQL 16.4 version manually since it apparently isn't in CDK enums yet
        pg_engine_version = rds.AuroraPostgresEngineVersion.of("16.4", "16")

        # Parameter Groups
        cluster_param_group = rds.ParameterGroup(
            self,
            "CustomClusterParamGroup",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=pg_engine_version),
            description="Contains unique parameters needed for: AWS Zero-ETL",
            parameters={
                "aurora.enhanced_logical_replication": "1",
                "aurora.logical_replication_backup": "0",
                "aurora.logical_replication_globaldb": "0",
                "rds.logical_replication": "1",
            },
        )

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
                "shared_preload_libraries": "pg_stat_statements,auto_explain",
            },
        )

        # Aurora PSQL 16.4 DB Cluster/Instances
        self.db_cluster = rds.DatabaseClusterFromSnapshot(
            self,
            "NightlyDBCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=pg_engine_version),
            snapshot_identifier="outlier-nightly-db-cluster-snapshot-03-11",
            cluster_identifier="outlier-nightly-db-cluster-cdk",
            writer=rds.ClusterInstance.serverless_v2("writer", scale_with_writer=True),
            readers=[
                rds.ClusterInstance.serverless_v2(
                    "reader1", scale_with_writer=False  # Will scale based on read load
                )
            ],
            serverless_v2_min_capacity=0.5,  # Min 0.5 ACU = ~1GB RAM
            serverless_v2_max_capacity=4,  # Max 4 ACU = ~8GB RAM
            port=5432,
            instance_identifier_base="outlier-nightly-db-cdk",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                availability_zones=["us-east-1b", "us-east-1c"],
            ),
            security_groups=[security_group],
            parameter_group=cluster_param_group,
            storage_encrypted=True,
            deletion_protection=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            cloudwatch_logs_exports=["postgresql"],
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
