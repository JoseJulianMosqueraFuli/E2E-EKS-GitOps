# E2E MLOps Platform on EKS

[![CI Pipeline](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml)
[![E2E (kind)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/e2e-kind.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/e2e-kind.yml)
[![ML Platform Image](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ml-platform-image.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ml-platform-image.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.0-blue)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-%3E%3D1.32-blue)](https://kubernetes.io/)
[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-brightgreen)](https://argoproj.github.io/cd/)

English | [Español](README.es.md)

End-to-end MLOps platform on Amazon EKS. From training to production with monitoring included.

> **Status (October 2026)**: GitOps manifests are complete and validated statically. The training path
> (Argo Workflows → MLflow → model registry with a promotion gate) is exercised end to end on kind in CI
> (`.github/workflows/e2e-kind.yml`). The first full deployment on AWS (`us-east-1`) is the next milestone.
> Pending work lives in [`backlog.md`](backlog.md).

## What is this?

A complete setup to run ML workloads on Kubernetes:

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Your ML Workflow                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Train Model ──► Register in MLflow ──► Deploy to KServe ──► Monitor│
│        │                  │                    │                │    │
│        ▼                  ▼                    ▼                ▼    │
│   ┌─────────┐      ┌───────────┐       ┌───────────┐    ┌─────────┐  │
│   │  Argo   │      │  MLflow   │       │  KServe   │    │ Grafana │  │
│   │Workflows│      │  Registry │       │  Serving  │    │Evidently│  │
│   └─────────┘      └───────────┘       └───────────┘    └─────────┘  │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                    Amazon EKS (Terraform)                            │
│         VPC │ EKS │ S3 │ ECR │ Glue │ KMS │ IAM                      │
└──────────────────────────────────────────────────────────────────────┘
```

## What you get

| Component                | Purpose                                              |
| ------------------------ | ---------------------------------------------------- |
| **Terraform modules**    | VPC, EKS, S3, ECR, Glue - reusable and tested        |
| **ML Platform**          | Ready-to-use models, training pipelines, CLI         |
| **`mlops-platform` image** | One container image for every pipeline step (`step split/train/evaluate/register`) |
| **Argo Workflows v4**    | Training pipeline with a promotion gate against the `@champion` model |
| **MLflow 2.22**          | Track experiments, model registry with aliases (own server image with PostgreSQL + S3 drivers) |
| **Kubeflow Pipelines**   | Optional pipeline UI/SDK (KFP 2.17.2)                |
| **KServe**               | Serve models with autoscaling                        |
| **Prometheus + Grafana** | Metrics, dashboards, and cost monitoring             |
| **Evidently**            | Detect data drift automatically                      |
| **Optional NVIDIA GPU**  | GPU node groups + GPU Operator for CUDA workloads    |
| **Istio mTLS**           | Strict mutual TLS between all MLOps services         |
| **Gatekeeper/OPA**       | Enforce Pod Security Standards via admission control |
| **Multi-environment**    | Dev, staging, prod configs                           |
| **CI/CD templates**      | GitHub Actions, GitLab, CircleCI, Jenkins            |
| **E2E smoke test**       | Argo + MLflow + training on kind, in GitHub Actions only |
| **AI agent rules**       | Shared rules + read-only MCP servers for Kiro, VS Code and Claude Code (`.agents/`) |

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

| Package            | Version  | Notes                                                    |
| ------------------ | -------- | -------------------------------------------------------- |
| MLflow             | 2.22.x   | Same version in the client (`poetry.lock`) and the server image |
| scikit-learn       | >= 1.3   | Model training (preprocessing + model saved as one pipeline) |
| pandas / pyarrow   | 2.x / >= 14 | CSV and Parquet, local paths or `s3://`               |
| Great Expectations | 1.x      | Optional extra `validation`                              |
| Evidently          | 0.7.x    | Optional extra `monitoring`                              |
| Feast              | 0.40.x   | Optional extra `features`                                |
| Argo Workflows     | v4.0.13  | Pipeline orchestration                                   |
| Kubeflow Pipelines | 2.17.2   | Optional                                                 |

> Full dependency list and extras in `ml-platform/pyproject.toml`. `poetry install -E dev` installs
> everything needed for the test suite; the container image installs only the core dependencies.

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

Target account `231629457413`, region `us-east-1`. Before the first `apply`:

1. Bootstrap the Terraform backend once per environment: `./scripts/bootstrap-terraform-backend.sh dev us-east-1`
   (see HIGH-001 in [`critical.md`](critical.md)).
2. S3 bucket names are global: confirm the names used by Terraform and the manifests are free in S3.
3. Container images are referenced from ECR (`mlops-<env>-trainer`, `mlops-<env>-mlflow-server`);
   publishing to ECR from CI needs an OIDC role (pending, see [`backlog.md`](backlog.md)).

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# 1. Deploy infrastructure
make init ENV=dev
make plan ENV=dev
make apply ENV=dev

# 2. Configure kubectl
aws eks update-kubeconfig --name mlops-dev-cluster --region us-east-1

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
│   ├── src/                  # Models, data processing, CLI (incl. `step` commands)
│   ├── tests/                # Unit and integration tests
│   ├── Dockerfile            # `mlops-platform` image (builder / test / runtime stages)
│   ├── Dockerfile.mlflow-server  # MLflow server with PostgreSQL + S3 drivers
│   └── pyproject.toml        # Python packaging with optional extras
├── ci-cd/                    # CI/CD configurations (Jenkins)
├── scripts/                  # Automation scripts
│   └── e2e/                  # kind smoke test (runs in GitHub Actions)
├── .github/workflows/        # CI, image build, E2E on kind, environment promotion
├── .agents/                  # AI agent rules and MCP servers (source of truth)
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

# Validate data (needs the `validation` extra)
poetry run python -m src.cli validate data/production.csv --create-suite

# Pipeline steps (what each Argo task runs inside the `mlops-platform` image)
poetry run python -m src.cli step split    --input data/sample.csv --output data/run --outputs-dir out
poetry run python -m src.cli step train    --features data/run/train.parquet --model-name clf --experiment-name dev --outputs-dir out
poetry run python -m src.cli step evaluate --model-uri "$(cat out/model-uri.txt)" --test-data data/run/test.parquet --model-name clf --outputs-dir out
poetry run python -m src.cli step register --model-uri "$(cat out/model-uri.txt)" --model-name clf --outputs-dir out
```

`step evaluate` approves a candidate only if it reaches `--min-score` and beats the model holding the
`@champion` alias by `--min-improvement`; `step register` assigns that alias to the new version.

### CI workflows

| Workflow                       | What it does                                                          |
| ------------------------------ | --------------------------------------------------------------------- |
| `ci.yml`                       | Terraform, Kubernetes, Python and Helm validation + security scan     |
| `ml-platform-image.yml`        | Tests inside the image; publishes `mlops-platform` to GHCR (amd64, `sha-` tags) |
| `e2e-kind.yml`                 | Builds both images, creates kind and runs `scripts/e2e/kind-smoke.sh` |
| `environment-promotion.yml`    | Promotes changes between environments                                 |

GitHub-hosted runners are free for public repositories, so these workflows have no cost.

### Access Services

```bash
make port-forward-mlflow    # MLflow UI at localhost:5000
make port-forward-grafana   # Grafana at localhost:3000
make port-forward-kubeflow  # Kubeflow at localhost:8080
```

## Documentation

> **📚 Full index: [Documentation Hub](docs/README.md)** — the single entry point that catalogs every document and names the canonical source per topic. Quick links below.

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

| Resource                         | Cost/Hour      |
| -------------------------------- | -------------- |
| EKS Control Plane                | $0.10          |
| NAT Gateway                      | $0.045 + data  |
| EC2 t3.medium (x2 nodes, dev default) | $0.0416 each |

**Total for a 3-hour E2E test in `us-east-1`: ~$1 - $2 USD** (plus EBS, load balancers and data
transfer). On-demand prices; check current AWS pricing before running.

> Tip: Always run `make destroy ENV=dev` immediately after testing to avoid ongoing charges.

### Time Estimates

| Phase                                | Duration    |
| ------------------------------------ | ----------- |
| `terraform apply` (infrastructure)   | 15-25 min   |
| MLOps stack deployment (ArgoCD sync) | 10-15 min   |
| Full validation & tests              | 10-15 min   |
| `terraform destroy` (cleanup)        | 10-15 min   |
| **Total end-to-end**                 | **~1 hour** |

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

_Last updated: 2026-10-10_
