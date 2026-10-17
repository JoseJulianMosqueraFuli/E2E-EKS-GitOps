# Full platform guide

Architecture, components, setup, command reference, delivery workflows, and operating estimates for the EKS MLOps platform.

[Brief overview](../README.md) · [Documentation index](README.md) · [Español](platform-guide.es.md)

The training, evaluation, and registration flow has passed the kind E2E test in GitHub Actions.
The first full AWS deployment is pending. Check the [backlog](project/backlog.md) before deploying.
Start with GitHub Actions; the Python setup below is optional and does not require a local cluster.

## Table of Contents

- [What is this?](#what-is-this)
- [What you get](#what-you-get)
- [Prerequisites](#prerequisites)
- [Key Dependencies](#key-dependencies)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Documentation](#documentation)
- [Deployment Time & Cost Estimates](#deployment-time--cost-estimates)
- [Resilience and Chaos Engineering](#resilience-and-chaos-engineering)
- [Contributing](#contributing)
- [License](#license)

## What is this?

The platform connects the following stages of the ML lifecycle on Kubernetes:

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
| **Istio mTLS**           | mTLS policies; remaining coverage gaps are tracked in the backlog         |
| **Gatekeeper/OPA**       | Admission policies, including image-tag restrictions |
| **Multi-environment**    | Dev, staging, prod configs                           |
| **CI/CD templates**      | GitHub Actions, GitLab, CircleCI, Jenkins            |
| **E2E smoke test**       | Argo + MLflow + training on kind, in GitHub Actions only |
| **AI agent rules**       | Shared instructions in `AGENTS.md` and `.agents/`; minimal entry points for each tool |

## Prerequisites

| Task | Requirements |
|---|---|
| Inspect the project and run CI | GitHub access; tools are installed on the hosted runner |
| Generate an initial AWS plan | GitHub environment, AWS OIDC planning role, `AWS_PLAN_ROLE_ARN`, and `AWS_REGION`; see [Terraform CI](terraform-ci.md) |
| Work on Python code (optional) | Git, Python 3.10–3.12, and Poetry; install the component's dependencies |
| Operate an existing AWS environment | AWS CLI v2, an authorized AWS session, Terraform, kubectl, Kustomize, Helm, and Make on the execution host |
| Run infrastructure integration tests | Go 1.21 and AWS access; Terratest creates real resources |

Terraform roots declare `>= 1.0`; the [CI workflow](../.github/workflows/ci.yml) pins its own Terraform version.
Use the versions pinned in the workflows and dependency files when reproducing CI.
Configure AWS authentication on the execution host through your authorized profile/session; `aws configure`
is the CLI configuration entry point. GitHub Actions uses OIDC rather than stored access keys.

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

> Full dependency list and extras in [`ml-platform/pyproject.toml`](../ml-platform/pyproject.toml). `poetry install -E dev` installs
> everything needed for the test suite; the container image installs only the core dependencies.

## Quick Start

### Start here: GitHub Actions

1. Push a branch or open a pull request to run the applicable checks in **CI Pipeline**.
   Terraform validation covers dev, staging, and prod without AWS credentials.
2. Follow [Terraform CI setup](terraform-ci.md) to configure the planning role and environment variables.
   Run **Actions → Terraform Initial Plan → Run workflow** from `main`, selecting `dev` first.
   This plans from empty temporary state; it neither deploys resources nor compares existing infrastructure.
3. Run **Actions → E2E (kind) → Run workflow** to build the images and exercise training,
   evaluation, registration, and rejection of a candidate that fails the promotion gate.
   The temporary Kubernetes cluster runs on GitHub's runner.

These workflows are the initial validation path. AWS deployment remains a separate, pending milestone.

### Option A: Python development (optional, no local cluster)

Run these commands on a development host with sufficient resources. Set `TRAINING_RUN_ID` to the ID
printed by training before using the inference example. Use feature-only data for inference; see the
[ML guide](ml-platform-guide.md) for preparing input data and configuration.

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps/ml-platform

# Install with Poetry (recommended)
pip install poetry
poetry install -E dev

# Create sample data and train
poetry run python -m src.cli create-sample data/sample.csv --n-samples 1000
poetry run python -m src.cli train data/sample.csv
poetry run python -c 'import pandas as pd; pd.read_csv("data/sample.csv").drop(columns=["target"]).to_csv("data/input.csv", index=False)'

# Run inference
poetry run python -m src.cli inference data/input.csv \
    --model-path "artifacts/model_${TRAINING_RUN_ID}.joblib" \
    --output-path predictions.json
```

### Option B: Full AWS Deployment

This is the operational command reference for a configured execution host or a future deployment runner.
The initial-plan workflow does not perform these deployment steps. Before using them, resolve the
[deployment blockers](project/backlog.md): backend activation (HIGH-001), ArgoCD configuration injection
(#48), workload IRSA (#50), unique bucket names (#51), missing workflow images (#52), and ECR publishing (#55).
Install/configure Flux and ArgoCD using the [GitOps setup guide](../gitops/SETUP.md).
Use one deployment owner per resource; do not install the same application through Helm and ArgoCD.

Account and region come from `gitops/platform/aws.env` (not in git; copy it from `aws.env.example`, see
[`gitops/platform/README.md`](../gitops/platform/README.md)). Before the first `apply`:

1. Bootstrap the Terraform backend once per environment: `./scripts/bootstrap-terraform-backend.sh dev "${AWS_REGION}"`
   (see HIGH-001 in [`docs/project/critical.md`](project/critical.md)).
2. S3 bucket names are global: confirm the names used by Terraform and the manifests are free in S3.
3. Container images are referenced from ECR (`mlops-<env>-trainer`, `mlops-<env>-mlflow-server`);
   publishing to ECR from CI needs an OIDC role (pending, see [`docs/project/backlog.md`](project/backlog.md)).

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# 1. Deploy infrastructure
make init ENV=dev
make plan ENV=dev
make apply ENV=dev

# 2. Configure kubectl
aws eks update-kubeconfig --name mlops-dev-cluster --region "${AWS_REGION}"

# 3. Install MLOps stack
make mlops-core    # MLflow + Monitoring
# or
make mlops-full    # MLflow + Kubeflow + Monitoring

# 4. Access services
make port-forward-mlflow   # http://localhost:5000
make port-forward-grafana  # http://localhost:3000
```

## Project Structure

Canonical application manifests live in `gitops/applications/apps/<app>/base/`, with environment
overlays under `overlays/{dev,staging,production}/`. Terraform uses `infra/environments/{dev,staging,prod}/`.
The [architecture reference](architecture/implementation.md) explains ownership across Terraform, Flux, and ArgoCD.

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
    ├── architecture/         # Architecture overview
    ├── project/              # Backlog and critical findings
    ├── reports/              # Historical reports
    └── proposals/            # Proposed future work
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
| `make mlops-full`      | Install MLflow + Kubeflow + Monitoring |
| `make mlops-install MLOPS_TOOLS=mlflow,kubeflow,kserve,monitoring` | Select tools explicitly, including KServe |
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
[ "$(cat out/model-approved.txt)" = "true" ] && \
poetry run python -m src.cli step register --model-uri "$(cat out/model-uri.txt)" --model-name clf --outputs-dir out
```

The examples above run from `ml-platform/`. `step split` writes train/test datasets; `step train`
logs the candidate and writes its URI to `out/model-uri.txt`. Evaluation writes a decision to
`out/model-approved.txt`; registration must consume that decision. The Argo training template enforces
this gate. The individual `register` command does not replace orchestration checks.

`step evaluate` approves a candidate only if it reaches `--min-score` and beats the model holding the
`@champion` alias by `--min-improvement`; `step register` assigns that alias to the new version.

### CI workflows

| Workflow                       | What it does                                                          |
| ------------------------------ | --------------------------------------------------------------------- |
| [ci.yml](../.github/workflows/ci.yml)                       | Terraform validation for dev/staging/prod, Kubernetes, Python and Helm + security scan |
| [terraform-plan.yml](../.github/workflows/terraform-plan.yml)           | Manual initial AWS plans through read-only OIDC; no apply |
| [ml-platform-image.yml](../.github/workflows/ml-platform-image.yml)        | Tests inside the image; publishes `mlops-platform` to GHCR (amd64, `sha-` tags) |
| [e2e-kind.yml](../.github/workflows/e2e-kind.yml)                 | Builds both images, creates kind and runs `scripts/e2e/kind-smoke.sh` |
| [environment-promotion.yml](../.github/workflows/environment-promotion.yml)    | Promotes changes between environments                                 |

See [Terraform CI setup](terraform-ci.md) for OIDC, workflow permissions, billing references, and the
limitations of empty-state plans. The Terraform plan runs entirely on GitHub Actions.

### Access Services

```bash
make port-forward-mlflow    # MLflow UI at localhost:5000
make port-forward-grafana   # Grafana at localhost:3000
make port-forward-kubeflow  # Kubeflow at localhost:8080
```

## Documentation

> **📚 Full index: [Documentation Hub](README.md)** — the single entry point that catalogs every document and names the canonical source per topic. Quick links below.

| Document                                                              | Description                            |
| --------------------------------------------------------------------- | -------------------------------------- |
| [Quick Start Guide](quick-start-guide.md)                        | Step-by-step setup                     |
| [ML Platform Guide](ml-platform-guide.md)                        | ML platform details                    |
| [Model Monitoring](model-monitoring-guide.md)                    | Drift detection setup                  |
| [Security](security-best-practices.md)                           | Security guidelines (mTLS, Gatekeeper) |
| [GPU Operator Setup](../gitops/applications/apps/gpu-operator/README.md) | Optional NVIDIA GPU on EKS             |

## Deployment Time & Cost Estimates

The following figures preserve the earlier README's planning assumptions; they are not a verified
current quote or measured deployment results. For the broader breakdown, including GPU nodes and
multiple environments, see [cost estimation](cost-estimation.md).

### AWS cost assumptions from the earlier README

| Resource                         | Cost/Hour      |
| -------------------------------- | -------------- |
| EKS Control Plane                | $0.10          |
| NAT Gateway                      | $0.045 + data  |
| EC2 t3.medium (x2 nodes, dev default) | $0.0416 each |

**Earlier working estimate for a 3-hour E2E run: ~$1–$2 USD**, plus EBS, load balancers, and data transfer. Recalculate for `AWS_REGION`, the actual node count, and the selected instance types before allocating a budget.

> For a disposable test environment, plan and review cleanup with `make destroy ENV=dev` after collecting results and preserving needed data. It destroys the resources managed by that environment; it is not a routine validation command.

### Time Estimates

| Phase                                | Duration    |
| ------------------------------------ | ----------- |
| `terraform apply` (infrastructure)   | 15-25 min   |
| MLOps stack deployment (ArgoCD sync) | 10-15 min   |
| Full validation & tests              | 10-15 min   |
| `terraform destroy` (cleanup)        | 10-15 min   |
| **Total end-to-end**                 | **~1 hour** |

## Resilience and Chaos Engineering

Litmus provides pod deletion, resource stress, node drain, and zone-eviction experiments.
The first validation target is MLflow in dev: check readiness, start an availability probe, inject a
pod deletion, check the result and recovery, and log a new MLflow run.

The zone workflow simulates pod eviction through taints; it does not reproduce loss of AWS networking
or storage. Network partition is stopped until isolation is demonstrated (#59). Effective permissions
and recovery after aborts still need verification on EKS (#60).

See the [Chaos runbook](../gitops/applications/apps/chaos/README.md) for prerequisites, commands,
pass/fail criteria, cleanup, and the [adoption plan](chaos-engineering-proposal.md) for later phases.

## Contributing

Follow the [contribution guide](contributing.md) and use GitHub Actions for the applicable checks.
The optional development commands below preserve the full setup reference. `make test` is Terratest:
it uses real AWS and is only for an explicitly planned infrastructure test, not an ordinary contribution check.

### How to Contribute

1. Fork the repository
2. Create your branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Review the GitHub Actions checks; optionally run `make validate-all` on the development host
5. Commit: `git commit -m 'feat(ml): add model support'`
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

This project is licensed under the MIT License - see [LICENSE](../LICENSE) for details.

---

Built by [Jose Julian Mosquera](https://github.com/JoseJulianMosqueraFuli)

_Last updated: 2026-10-17_
