# from aws_cdk import aws_ec2 as ec2
# from aws_cdk import aws_rds as rds
# import aws_cdk as cdk
# from constructs import Construct
# from .base_construct import BaseConstruct
#
# class DatabaseConstruct(BaseConstruct):
#     def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc, rds_security_groups: list[ec2.ISecurityGroup]):
#         super().__init__(scope, id)
#
#         # RDS subnet group
#         self.subnet_group = rds.SubnetGroup(
#             self,
#             "RdsSubnetGroup",
#             vpc=vpc,
#             subnet_group_name="outlier-nightly-subnet-group-test-2",
#             description="Subnet group for outlier nightly RDS",
#             vpc_subnets=ec2.SubnetSelection(
#                 subnets=[
#                     ec2.Subnet.from_subnet_id(
#                         self,
#                         f"Subnet{i}",
#                         subnet_id
#                     ) for i, subnet_id in enumerate([
#                         "subnet-0a92401d83e646775",
#                         "subnet-031293b41be863713",
#                         "subnet-0105fa1e5a7b370c4"
#                     ])
#                 ]
#             )
#         )
#
#         # RDS instance
#         self.db_instance = rds.DatabaseInstance(
#             self,
#             "RdsInstance",
#             instance_identifier="outlier-nightly-test-2",
#             database_name="outlier_nightly",
#             engine=rds.DatabaseInstanceEngine.postgres(
#                 version=rds.PostgresEngineVersion.VER_12
#             ),
#             instance_type=ec2.InstanceType.of(
#                 ec2.InstanceClass.T3,
#                 ec2.InstanceSize.LARGE
#             ),
#             vpc=vpc,
#             subnet_group=self.subnet_group,
#             security_groups=rds_security_groups,
#             allocated_storage=125,
#             storage_type=rds.StorageType.GP3,
#             iops=3000,
#             storage_throughput=125,
#             storage_encrypted=False,
#             backup_retention=cdk.Duration.days(7),
#             preferred_backup_window="06:17-06:47",
#             preferred_maintenance_window="sun:06:51-sun:07:21",
#             auto_minor_version_upgrade=False,
#             deletion_protection=False,
#             copy_tags_to_snapshot=False,
#             cloudwatch_logs_exports=["postgresql", "upgrade"],
#             enable_performance_insights=False,
#             monitoring_interval=cdk.Duration.seconds(0),
#             port=5432,
#             multi_az=False,
#             publicly_accessible=False,
#             parameter_group=rds.ParameterGroup.from_parameter_group_name(
#                 self,
#                 "ParamGroup",
#                 "default.postgres12"
#             ),
#             option_group=rds.OptionGroup.from_option_group_name(
#                 self,
#                 "OptionGroup",
#                 "default:postgres-12"
#             ),
#             allow_major_version_upgrade=False,
#         )
#
#         # Add tags
#         cdk.Tags.of(self.db_instance).add("bounded_context", "outlier")
#         cdk.Tags.of(self.db_instance).add("env", self.environment)
#         cdk.Tags.of(self.subnet_group).add("bounded_context", "outlier")
#         cdk.Tags.of(self.subnet_group).add("env", self.environment)
#
#     @property
#     def db_endpoint(self) -> str:
#         return self.db_instance.instance_endpoint.hostname
#
#     @property
#     def db_port(self) -> int:
#         return self.db_instance.instance_endpoint.port