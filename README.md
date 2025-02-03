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

#### What AWS Resources are ✅ managed by this project?
- Our core application stack.
  - ✅ ECR (App Images)
  - ✅ ALB (App Load Balancer)
  - ✅ ECS (App Containers)
  - ✅ RDS (App Database)
  - ✅ CodePipeline (App CI/CD)
  - ✅ S3 Buckets for Application (App Blob Storage)

#### What AWS Resources are NOT ❌ managed by this project?
- Any non-core application resources.
- ❌ Task Definitions
  - These live inside our application repositories. see `outlier-api/taskdef_nightly.json`
- ❌ Secrets Manager 
  - It is not good practice to manage Secrets Manager resources in this code. Instead, we actually fetch Secrets dynamically in this project, as needed.
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
.
├── cdk.json
├── poetry.lock
├── pyproject.toml
├── README.md
├── src
│  ├── __init__.py
│  ├── app.py
│  ├── assets
│  │  ├── ecs
│  │  │  └── hello-world
│  │  │     └── Dockerfile
│  │  └── lambda
│  │     └── hello-world
│  │        └── lambda_function.py
│  ├── bin
│  │  ├── cicd_helper.py
│  │  ├── env_helper.py
│  │  └── git_helper.py
│  ├── custom_constructs
│  │  ├── __init__.py
│  │  ├── base_construct.py
│  │  ├── network_construct.py
│  │  └── README.md
│  └── stacks
│     ├── __init__.py
│     ├── base_stack.py
│     ├── github_oidc_stack.py
│     └── README.md
└── tests
   ├── __init__.py
   └── test_example.py
```

### Section Details
- **`src/assets`:** Contains application code for Lambda functions and ECS services.
- **`src/bin`:** Includes utility scripts for environment setup and CI/CD integration.
- **`src/custom_constructs`:** Houses reusable constructs for infrastructure components.
- **`src/stacks`:** Defines AWS stacks for deploying collections of resources.
- **`tests`:** Contains unit and integration tests.

This structure ensures maintainability, scalability, and efficient collaboration across Outlier's infrastructure projects.