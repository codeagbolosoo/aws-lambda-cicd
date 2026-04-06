# 🚀 Python Lambda CI/CD Pipeline

**Author:** Abraham Agbolosoo
**GitHub:** [@codeagbolosoo](https://github.com/codeagbolosoo)
**Stack:** Python 3.12 · AWS Lambda · AWS CodePipeline · Docker · ECR

A production-ready CI/CD pipeline for deploying Python applications to AWS Lambda using container images. Includes automated testing, security scanning, staged deployments, and canary traffic shifting.

## Pipeline Overview

Source → Test (pytest) → Build (Docker→ECR) → Security Scan → Deploy Staging → Approve → Deploy Prod

| Stage | Tool | Description |
|---|---|---|
| Source | GitHub | Triggers on push to main |
| Test | CodeBuild + pytest | Unit tests with 80% coverage gate |
| Build | CodeBuild + Docker | Builds image, pushes to ECR with commit SHA |
| Security | Bandit + pip-audit | SAST + dependency CVE scan |
| Deploy Staging | CodeBuild + Lambda | Auto-deploys to staging alias, runs smoke test |
| Approve | SNS email | Manual gate before production |
| Deploy Prod | CodeBuild + CodeDeploy | Canary 10% then 100% with auto-rollback |

## Quick Start

    git clone https://github.com/codeagbolosoo/aws-lambda-cicd.git
    cd aws-lambda-cicd
    pip install -r requirements-dev.txt
    cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1
    cdk deploy --context account=YOUR_ACCOUNT_ID --context region=us-east-1

## License

MIT (c) Abraham Agbolosoo
