import os

from projen import github
from projen.awscdk import AwsCdkPythonApp

from src.bin.cicd_helper import github_cicd
from src.bin.env_helper import cdk_action_task

# Define the python module name and set the python version
python_module_name = "src"
python_version = "3.11"

# Define the AWS region for the CDK app and github workflows
# Default to us-east-1 if AWS_REGION is not set in your environment variables
aws_region = os.getenv("AWS_REGION", "us-east-1")

project = AwsCdkPythonApp(
    author_email="dobson.dunavant@savvas.com",
    author_name="Dobson Dunavant",
    cdk_version="2.153.0",  # Find the latest CDK version here: https://pypi.org/project/aws-cdk-lib/
    cdk_version_pinning=True,
    module_name=python_module_name,
    name="outlier-aws-infrastructure",
    license="Apache-2.0",
    description="Create and deploy an AWS CDK app that will manage the infra for 1 or more AWS account(s) using GitHub actions.",
    version="0.1.0",
    poetry=True,
    app_entrypoint=f"{python_module_name}/app.py",
    deps=["aws-cdk-github-oidc"],
    dev_deps=[
        "projen@0.85.2",
        "ruff",
    ],  # Find the latest projen version here: https://pypi.org/project/projen/
    github_options={"pull_request_lint": False, "workflows": True},
    git_ignore_options={
        "ignore_patterns": [
            "__pycache__",
            "__pycache__/",
            ".python-version",
            "!.eslintrc.js",
            ".cache",
            ".coverage.*",
            ".coverage",
            ".DS_Store",
            ".env",
            ".mypy_cache",
            ".pytest_cache",
            ".Python",
            ".venv/",
            ".vscode",
            "*.js",
            "*.log",
            "*.manifest",
            "*.pyc",
            "*.spec",
            "*.zip",
            "**/cdk-test-report.xml",
            "*node_modules*",
            "build/",
            "coverage/",
            "dist/",
            "downloads/",
            "env/",
            "ENV/",
            "htmlcov/",
            "sdist/",
            "var/",
            "venv/",
            "former_2_output.py",
        ],
    },
)

# Set the CDK_DEFAULT_REGION environment variable for the projen tasks,
# so the CDK CLI knows which region to use
project.tasks.add_environment("CDK_DEFAULT_REGION", aws_region)

# First remove the existing task
project.tasks.remove_task("install:ci")

# Then add our modified version
project.tasks.add_task(
    "install:ci", exec="poetry check --lock && poetry install --no-root"
)

# Define the target AWS accounts for the different environments
target_accounts = {
    "nightly": "528757783796",
    "production": None,
}

gh = github.GitHub(project)
# Loop through each environment in target_accounts
for env, account in target_accounts.items():
    if account:  # Check if account is not None
        # Adds customized projen tasks for executing cdk actions for each environment
        cdk_action_task(
            project,
            {
                "CDK_DEFAULT_ACCOUNT": account,
                "ENVIRONMENT": env,
            },
        )

        # Adds GitHub action workflows for deploying the CDK stacks to the target AWS account
        github_cicd(gh, account, env, python_version)  # Python 3.11

project.synth()
