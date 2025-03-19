# Outlier AWS CDK Infrastructure (Python)

[![Build Status](https://github.com/dannysteenman/aws-cdk-starterkit/actions/workflows/build.yml/badge.svg)](https://github.com/...build.yml) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Overview

This repository contains Outlier's AWS CDK project. It defines infrastructure as code for the organization's Nightly AWS account using AWS CDK in Python. The project leverages AWS CDK, Projen, and GitHub Actions for streamlined and efficient deployments to Outlier's AWS environments.

---

## Features

- **Streamlined Setup:** Quickly configure the project through a single configuration file ([`.projenrc.py`](./.projenrc.py)).
- **Multi-Account Support:** Provides flexibility for managing multiple AWS accounts across various environments.
- **Automated Deployment Pipelines:** Pre-configured GitHub Actions workflows automate deployment processes.
- **Organized Project Structure:** Logical and intuitive structure for managing constructs and stacks.
- **Secure Deployments:** Utilizes OpenID Connect for secure, credential-less GitHub Actions authentication with AWS.
- **Dependency Management:** Handles dependencies and virtual environments using Poetry.
- **Fast Linting and Formatting:** Includes Ruff for efficient linting and formatting.
- **Enhanced PR Process:** Built-in pull request templates streamline code reviews.

---

#### Which Outlier AWS Resources are ✅ managed by this project?
- Our core application stack.
  - ✅ ECR (App Build Images)
  - ✅ ALB (App Load Balancer)
  - ✅ ECS (App Containers)
  - ✅ Aurora PSQL 16.4 (App Database)
  - ✅ CodePipeline (App CI/CD)
  - ✅ S3 Buckets for Application (App Blob Storage)
  - ✅ Application IAM Users, Roles, and Policies
  - ✅ Route53 A Record - "api.nightly.savvasoutlier.com"
    - We are ONLY managing this one record and NO other Route53 infrastructure in this project.
    - Why? Because of how tightly coupled the A record and the ALB are, it made the most sense to me to keep them managed in the same place. -Dobson

#### Which Outlier AWS Resources are NOT ❌ managed by this project?
- Any non-core application resources.
  - ❌ VPC and other high-level networking resources
    - Why? Savvas IFT manages our high-level networking resources themselves, through Iaac (Terraform/CDK). We do not want to have 2 separate IaaC projects trying to manage the same resources. 
    - Because of this, we are not and SHOULD NOT be managing any AWS Resources that have `terraform_managed = True` as a tag.
    - We do, however, dynamically import and reference these values in this project.
  - ❌ Task Definitions
    - Why? These live inside our application repositories and are dynamically generated and used by our AWS CodePipeline. see `outlier-api/taskdef_nightly.json`
  - ❌ Secrets Manager 
    - Why? It is not good practice to manage Secrets Manager resources in this code. 
    - We do, however, dynamically fetch/import and reference these values in this project as needed.
  - ❌ ACM Certificates
    - Why? Certificates often have their own lifecycle outside of the core application resources, sometimes with other Savvas parties needing to make changes to them. Because of this, I chose to leave their management in the AWS console. 
    - We do, however, dynamically import and reference these values in this project.
  - ❌ Route53 / Hosted Zones (not the api.nightly.savvasoutlier.com A record itself, we are managing that in the CDK 100%)
    - Why? We have different types of stakeholders that would like visibility and control over this, outside of the CDK.
    - We do, however, dynamically import and reference these values in this project.
  - ❌ Redshift (Data Warehouse)
  - ❌ Firehose, DMS, DataSync and other non-application-stack services.

---

## Setup Instructions

### Steps to Configure and Deploy

1. **Clone the Repository:** Clone this repository to a local environment.
2. **Configure GitHub Access:** Add a Personal Access Token in the repository settings on GitHub following [these instructions](https://projen.io/docs/integrations/github/#fine-grained-personal-access-token-beta).
3. **Install Required Tools:** Install AWS CDK and Projen globally:
   ```bash
   npm install -g aws-cdk projen
   ```
4. **Install Dependencies:** Install project dependencies with Poetry:
   ```bash
   poetry install
   ```
5. **Configure Project Settings:** Modify the AWS region and account IDs in the [.projenrc.py](./.projenrc.py) file:
   ```python
   aws_region = os.getenv("AWS_REGION", "us-east-1")
   target_accounts = {
       "dev": "987654321012",
       "test": "123456789012",
       "staging": None,
       "production": None,
   }
   ```
6. **Generate Workflow Files:** Run Projen to generate GitHub Actions workflow files:
   ```bash
   projen
   ```
7. **Authenticate AWS CLI:** Log in to the appropriate AWS account using the AWS CLI. Follow [this guide](https://towardsthecloud.com/set-up-aws-cli-aws-sso) if necessary.
8. **Bootstrap CDK Environment:** Deploy the CDK toolkit stack if not already set up:
   ```bash
   cdk bootstrap
   ```
9. **Deploy GitHub OIDC Stack:** Enable GitHub Actions to deploy resources by executing:
   ```bash
   projen dev:deploy
   ```
10. **Commit and Push Changes:** Push changes to the `main` branch to trigger the deployment pipeline.

---

## Project Structure

The project is organized into logical units to facilitate maintainability and scalability:

```bash
├── README.md
├── cdk.json
├── poetry.lock
├── pyproject.toml
├── src
│   ├── __init__.py
│   ├── app.py
│   ├── assets
│   │   ├── ecs
│   │   │   └── hello-world
│   │   │       └── Dockerfile
│   │   └── lambda
│   │       └── hello-world
│   │           └── lambda_function.py
│   ├── bin
│   │   ├── cicd_helper.py
│   │   ├── env_helper.py
│   │   └── git_helper.py
│   ├── custom_constructs
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── alb_construct.py
│   │   ├── base_construct.py
│   │   ├── database_construct.py
│   │   ├── ecr_construct.py
│   │   ├── ecs_construct.py
│   │   ├── iam_construct.py
│   │   ├── network_construct.py
│   │   ├── pipeline_construct.py
│   │   ├── storage_construct.py
│   │   └── waf_construct.py
│   └── stacks
│       ├── README.md
│       ├── __init__.py
│       ├── base_stack.py
│       ├── dev_application_stack.py
│       ├── github_oidc_stack.py
│       └── nightly_application_stack.py
└── tests
    ├── __init__.py
    └── test_example.py

11 directories, 31 files
```

### Section Details
- **`src/assets`:** Contains application code for Lambda functions and ECS services.
- **`src/bin`:** Includes utility scripts for environment setup and CI/CD integration.
- **`src/custom_constructs`:** Houses reusable constructs for infrastructure components.
- **`src/stacks`:** Defines AWS stacks for deploying collections of resources.
- **`tests`:** Contains unit and integration tests.

This structure ensures maintainability, scalability, and efficient collaboration across Outlier's infrastructure projects.
