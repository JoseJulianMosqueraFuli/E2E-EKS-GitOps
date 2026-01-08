# E2E MLOps Platform on EKS

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.0-blue)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-%3E%3D1.25-blue)](https://kubernetes.io/)

English | [Español](README.es.md)

End-to-end MLOps platform on Amazon EKS. From training to production with monitoring included.

> **Note**: ~~GitOps~~ - ArgoCD integration coming soon.

## What is this?

A complete setup to run ML workloads on Kubernetes:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Your ML Workflow                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Train Model ──► Register in MLflow ──► Deploy to KServe ──► Monitor
│        │                  │                    │                │   │
│        ▼                  ▼                    ▼                ▼   │
│   ┌─────────┐      ┌───────────┐       ┌───────────┐    ┌─────────┐│
│   │Kubeflow │      │  MLflow   │       │  KServe   │    │ Grafana ││
│   │Pipelines│      │  Registry │       │  Serving  │    │Evidently││
│   └─────────┘      └───────────┘       └───────────┘    └─────────┘│
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                    Amazon EKS (Terraform)                           │
│         VPC │ EKS │ S3 │ ECR │ Glue │ KMS │ IAM                    │
└─────────────────────────────────────────────────────────────────────┘
```

## What you get

| Component                | Purpose                                       |
| ------------------------ | --------------------------------------------- |
| **Terraform modules**    | VPC, EKS, S3, ECR, Glue - reusable and tested |
| **ML Platform**          | Ready-to-use models, training pipelines, CLI  |
| **MLflow**               | Track experiments, register models            |
| **Kubeflow**             | Orchestrate ML workflows                      |
| **KServe**               | Serve models with autoscaling                 |
| **Prometheus + Grafana** | Metrics and dashboards                        |
| **Evidently**            | Detect data drift automatically               |
| **Multi-environment**    | Dev, staging, prod configs                    |
| **CI/CD templates**      | GitHub Actions, GitLab, CircleCI, Jenkins     |

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

```bash
# Required tools
terraform >= 1.0
kubectl >= 1.25
helm >= 3.0
aws-cli >= 2.0
python >= 3.9
make

# Configure AWS
aws configure
```

## Quick Start

### Option A: Local ML Platform (no cloud required)

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps/ml-platform

pip install -r requirements.txt

# Create sample data and train
python src/main.py create-sample data/sample.csv --n-samples 1000
python src/main.py train data/sample.csv

# Run inference
python src/main.py inference data/sample.csv \
    --model-path artifacts/model_*.joblib \
    --output-path predictions.json
```

### Option B: Full AWS Deployment

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# 1. Deploy infrastructure
make init ENV=dev
make plan ENV=dev
make apply ENV=dev

# 2. Configure kubectl
aws eks update-kubeconfig --name mlops-dev-cluster --region us-west-2

# 3. Install MLOps stack
make mlops-core    # MLflow + Monitoring
# or
make mlops-full    # Full stack (MLflow + Kubeflow + KServe + Monitoring)

# 4. Access services
make port-forward-mlflow   # http://localhost:5000
make port-forward-grafana  # http://localhost:3000
```

## Project Structure

```
.
├── infra/                    # Terraform infrastructure
│   ├── modules/              # Reusable modules (vpc, eks, s3, ecr, glue)
│   └── environments/         # Environment configs (dev, staging, prod)
├── k8s/                      # Kubernetes manifests
│   └── mlops-stack/          # MLflow, Kubeflow, KServe, monitoring
├── ml-platform/              # ML code and pipelines
│   └── src/                  # Models, data processing, CLI
├── ci-cd/                    # CI/CD configurations
├── scripts/                  # Automation scripts
└── docs/                     # Documentation
```

## Usage

### Infrastructure

| Command                | Description            |
| ---------------------- | ---------------------- |
| `make init ENV=dev`    | Initialize Terraform   |
| `make plan ENV=dev`    | Preview changes        |
| `make apply ENV=dev`   | Apply changes          |
| `make destroy ENV=dev` | Destroy infrastructure |

### MLOps Stack

| Command                | Description                 |
| ---------------------- | --------------------------- |
| `make mlops-core`      | Install MLflow + Monitoring |
| `make mlops-full`      | Install full stack          |
| `make mlops-status`    | Check status                |
| `make mlops-uninstall` | Uninstall stack             |

### ML Platform CLI

```bash
# Train
python src/main.py train data/dataset.csv

# Inference
python src/main.py inference data/input.csv --model-path artifacts/model.joblib

# Validate data
python src/main.py validate data/production.csv --create-suite
```

### Access Services

```bash
make port-forward-mlflow    # MLflow UI at localhost:5000
make port-forward-grafana   # Grafana at localhost:3000
make port-forward-kubeflow  # Kubeflow at localhost:8080
```

## Documentation

| Document                                           | Description           |
| -------------------------------------------------- | --------------------- |
| [Quick Start Guide](docs/quick-start-guide.md)     | Step-by-step setup    |
| [ML Platform Guide](docs/ml-platform-guide.md)     | ML platform details   |
| [Model Monitoring](docs/model-monitoring-guide.md) | Drift detection setup |
| [Security](docs/security-best-practices.md)        | Security guidelines   |

## Contributing

Contributions are welcome! Please read the guidelines below.

### How to Contribute

1. Fork the repository
2. Create your branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `make validate-all && make test`
5. Commit: `git commit -m 'Add my feature'`
6. Push: `git push origin feature/my-feature`
7. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# Install dev dependencies
cd ml-platform && pip install -r requirements-dev.txt

# Run tests
make test
```

### Code Style

- Terraform: Use `terraform fmt`
- Python: Follow PEP 8
- Kubernetes: Use `kubectl apply --dry-run=client`

### Reporting Issues

- Use GitHub Issues
- Include steps to reproduce
- Add relevant logs or screenshots

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

Built by [Jose Julian Mosquera](https://github.com/JoseJulianMosqueraFuli)
