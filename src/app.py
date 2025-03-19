import os

import aws_cdk as cdk
from stacks.base_stack import BaseStack
from stacks.dev_application_stack import DevApplicationStack
from stacks.github_oidc_stack import GitHubOIDCStack
from stacks.nightly_application_stack import NightlyApplicationStack

# Inherit environment variables from npm run commands (displayed in .projen/tasks.json)
environment = os.environ.get("ENVIRONMENT", "nightly")
aws_environment = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
)

# Instantiate the CDK app
app = cdk.App()

# Add GitHub OpenID Connect support and create an IAM role for GitHub
GitHubOIDCStack(app, f"GitHubOIDCStack-{environment}", env=aws_environment)

# Create a base stack which contains all of our global, shared resources
BaseStack(app, f"BaseStack-{environment}", env=aws_environment)

NightlyApplicationStack(app, f"NightlyApplicationStack-{environment}", env=aws_environment)

DevApplicationStack(app, f"DevApplicationStack-{environment}", env=aws_environment)


# Tag all resources in CloudFormation with the environment name
cdk.Tags.of(app).add("Environment", environment)

# Tag all resources in CloudFormation with the environment name
cdk.Tags.of(app).add("aws-cdk-managed", "True")

# Tag all resources in CloudFormation with the environment name
cdk.Tags.of(app).add("Project", "outlier-aws-infrastructure")

# Synthesize the CDK app
app.synth()
