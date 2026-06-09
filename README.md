# E2E MLOps Platform on EKS

[![CI Pipeline](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.0-blue)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-%3E%3D1.30-blue)](https://kubernetes.io/)
[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-brightgreen)](https://argoproj.github.io/cd/)

English | [Español](README.es.md)

End-to-end MLOps platform on Amazon EKS. From training to production with monitoring included.

> **Note**: GitOps with ArgoCD and Flux is fully implemented. See the `gitops/` directory.

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

| Component                | Purpose                                              |
| ------------------------ | ---------------------------------------------------- |
| **Terraform modules**    | VPC, EKS, S3, ECR, Glue - reusable and tested        |
| **ML Platform**          | Ready-to-use models, training pipelines, CLI         |
| **MLflow**               | Track experiments, register models                   |
| **Kubeflow**             | Orchestrate ML workflows                             |
| **KServe**               | Serve models with autoscaling                        |
| **Prometheus + Grafana** | Metrics, dashboards, and cost monitoring             |
| **Evidently**            | Detect data drift automatically                      |
| **Optional NVIDIA GPU**  | GPU node groups + GPU Operator for CUDA workloads    |
| **Istio mTLS**           | Strict mutual TLS between all MLOps services         |
| **Gatekeeper/OPA**       | Enforce Pod Security Standards via admission control |
| **Multi-environment**    | Dev, staging, prod configs                           |
| **CI/CD templates**      | GitHub Actions, GitLab, CircleCI, Jenkins            |

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
python >= 3.10
go >= 1.21
make

# Configure AWS
aws configure
```

## Key Dependencies

| Package            | Version | Notes                                |
| ------------------ | ------- | ------------------------------------ |
| MLflow             | >= 2.18 | Experiment tracking & model registry |
| Great Expectations | >= 0.17 | Data validation (1.x fluent API)     |
| Evidently          | >= 0.4  | Data drift detection                 |
| scikit-learn       | >= 1.3  | Model training                       |
| Kubernetes         | >= 27.2 | Cluster management                   |

> Full dependency list and optional extras in `ml-platform/pyproject.toml`. Install with Poetry.

## Quick Start

### Option A: Local ML Platform (no cloud required)

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps/ml-platform

# Install with Poetry (recommended)
pip install poetry
poetry install -E dev

# Create sample data and train
poetry run python -m src.cli create-sample data/sample.csv --n-samples 1000
poetry run python -m src.cli train data/sample.csv

# Run inference
poetry run python -m src.cli inference data/sample.csv \
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
├── k8s/                      # Kubernetes manifests (operational overlays)
│   ├── mlops-stack/          # MLflow, KServe, monitoring overlays
│   └── security/             # Istio mTLS, Gatekeeper policies
├── gitops/                   # GitOps source of truth (ArgoCD + Flux)
│   ├── applications/         # ArgoCD applications
│   │   ├── apps/             # mlflow, kubeflow, kserve, monitoring, gpu-operator
│   │   ├── environments/     # Per-environment overlays (dev/staging/production)
│   │   └── projects/         # ArgoCD projects + ApplicationSet
│   ├── charts/               # Helm charts (mlflow, kserve, kubeflow-pipelines, monitoring-stack)
│   ├── infrastructure/       # Flux-managed cluster infrastructure
│   │   ├── addons/           # EKS addons (ALB, EBS CSI, Autoscaler)
│   │   ├── clusters/         # Per-cluster bootstrap configs
│   │   ├── controllers/      # Flux + ArgoCD controllers
│   │   ├── networking/       # Ingress, Istio, Network Policies
│   │   ├── security/         # RBAC, IRSA, Pod Security
│   │   └── sources/          # Git and Helm repository sources
│   ├── scripts/              # Automation (install, promote, validate)
│   └── tests/                # Property-based tests (Hypothesis)
├── ml-platform/              # ML code and pipelines
│   ├── src/                  # Models, data processing, CLI
│   ├── tests/                # Unit and integration tests
│   └── pyproject.toml        # Python packaging with optional extras
├── ci-cd/                    # CI/CD configurations (Jenkins)
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
poetry run python -m src.cli train data/dataset.csv

# Inference
poetry run python -m src.cli inference data/input.csv --model-path artifacts/model.joblib

# Validate data
poetry run python -m src.cli validate data/production.csv --create-suite
```

### Access Services

```bash
make port-forward-mlflow    # MLflow UI at localhost:5000
make port-forward-grafana   # Grafana at localhost:3000
make port-forward-kubeflow  # Kubeflow at localhost:8080
```

## Documentation

| Document                                                              | Description                            |
| --------------------------------------------------------------------- | -------------------------------------- |
| [Quick Start Guide](docs/quick-start-guide.md)                        | Step-by-step setup                     |
| [ML Platform Guide](docs/ml-platform-guide.md)                        | ML platform details                    |
| [Model Monitoring](docs/model-monitoring-guide.md)                    | Drift detection setup                  |
| [Security](docs/security-best-practices.md)                           | Security guidelines (mTLS, Gatekeeper) |
| [GPU Operator Setup](gitops/applications/apps/gpu-operator/README.md) | Optional NVIDIA GPU on EKS             |

## Deployment Time & Cost Estimates

Running the full E2E test on AWS incurs real costs. Here is what to expect:

### AWS Costs (estimated for a single E2E run)

| Resource | Cost/Hour |
|----------|-----------|
| EKS Control Plane | $0.10 |
| NAT Gateway | $0.045 |
| EC2 m5.large (x2 nodes) | $0.192 each |

**Total for a 3-hour E2E test: ~$2.50 - $4.00 USD**

> Tip: Always run `make destroy ENV=dev` immediately after testing to avoid ongoing charges.

### Time Estimates

| Phase | Duration |
|-------|----------|
| `terraform apply` (infrastructure) | 15-25 min |
| MLOps stack deployment (ArgoCD sync) | 10-15 min |
| Full validation & tests | 10-15 min |
| `terraform destroy` (cleanup) | 10-15 min |
| **Total end-to-end** | **~1 hour** |

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

# Install dev dependencies with Poetry
cd ml-platform
pip install poetry
poetry install -E dev

# Run tests
poetry run pytest tests/ -v
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

*Last updated: June 2025*
