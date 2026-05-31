# E2E-EKS-GitOps: Implementation Overview

> **Project**: End-to-End MLOps Platform on Amazon EKS  
> **Author**: Jose Julian Mosquera  
> **License**: MIT  
> **Status**: Active development (Phase 2)

---

## 1. Project Purpose

End-to-end MLOps platform that enables ML workflows from **training to production** with monitoring, running on **Amazon EKS** and managed via **GitOps** (ArgoCD + Flux v2).

**Core Workflow:**

```
Train Model → Register in MLflow → Deploy to KServe → Monitor with Evidently + Grafana
```

**Key Goals:**

- Reusable Terraform infrastructure modules (VPC, EKS, S3, ECR, Glue)
- Local ML platform for development (no cloud required)
- Full AWS deployment for staging/production
- Automated CI/CD with multi-environment promotion
- Security-first design (mTLS, OPA/Gatekeeper, IRSA)

---

## 2. Technology Stack

### Infrastructure & Cloud

| Component    | Technology              | Purpose                     |
| ------------ | ----------------------- | --------------------------- |
| Orchestrator | Amazon EKS (>=1.25)     | Kubernetes cluster          |
| IaC          | Terraform (>=1.0)       | Infrastructure provisioning |
| Network      | VPC + NAT Gateway + ALB | Networking & ingress        |
| Storage      | S3 + EBS CSI            | Data & model artifacts      |
| Registry     | ECR                     | Docker images               |
| Catalog      | AWS Glue                | Data catalog & crawlers     |
| Encryption   | AWS KMS                 | At-rest encryption          |

### MLOps Platform

| Component           | Technology                  | Purpose                        |
| ------------------- | --------------------------- | ------------------------------ |
| Experiment Tracking | MLflow (>=2.18)             | Model registry & experiments   |
| Orchestration       | Kubeflow Pipelines          | ML workflow orchestration      |
| Model Serving       | KServe                      | Model serving with autoscaling |
| Monitoring          | Prometheus + Grafana        | Metrics & dashboards           |
| Drift Detection     | Evidently (>=0.4)           | Data drift detection           |
| Data Validation     | Great Expectations (>=0.17) | Data quality validation        |
| ML Framework        | scikit-learn (>=1.3)        | Model training                 |

### GitOps & Security

| Component          | Technology                | Purpose                 |
| ------------------ | ------------------------- | ----------------------- |
| GitOps Controllers | Flux v2 + ArgoCD          | Declarative deployments |
| Service Mesh       | Istio                     | mTLS between services   |
| Policy Enforcement | Gatekeeper / OPA          | Pod Security Standards  |
| Secret Management  | External Secrets Operator | Secure secret injection |
| Notifications      | ArgoCD Notifications      | Slack alerts            |

### CI/CD

| Provider       | Status            |
| -------------- | ----------------- |
| GitHub Actions | ✅ Primary        |
| GitLab CI      | ✅ Config present |
| CircleCI       | ✅ Config present |
| Jenkins        | ✅ Config present |

### Development

| Component       | Technology                 |
| --------------- | -------------------------- |
| Language        | Python (3.10 - 3.12)       |
| Package Manager | Poetry                     |
| CLI Framework   | Click                      |
| Testing         | pytest + Hypothesis        |
| Linting         | black, flake8, isort, mypy |
| Pre-commit      | detect-secrets             |

---

## 3. Repository Structure

```
E2E-EKS-GitOps/
├── infra/                          # Terraform infrastructure
│   ├── modules/                    # Reusable modules
│   │   ├── vpc/                    # VPC, subnets, NAT gateway
│   │   ├── eks/                    # EKS cluster, node groups, IRSA
│   │   ├── s3/                     # S3 buckets with lifecycle policies
│   │   ├── ecr/                    # ECR repositories with scanning
│   │   └── glue/                   # Glue catalog, crawlers, data quality
│   └── environments/               # Per-environment configs
│       ├── dev/                    # Dev environment (local backend)
│       ├── staging/                # Staging environment
│       └── prod/                   # Production environment
│
├── k8s/                            # Raw Kubernetes manifests
│   ├── mlops-stack/                # Operational overlays
│   │   ├── mlflow/                 # MLflow deployment (Kustomize)
│   │   ├── kserve/                 # KServe deployment
│   │   ├── monitoring/             # Prometheus + Grafana
│   │   ├── secrets/                # External Secrets configs
│   │   ├── argo-workflows/         # A/B testing workflows
│   │   ├── kubeflow-README.md      # Kubeflow setup guide (uses Helm chart)
│   │   └── seldon-README.md        # Seldon alternative reference
│   └── security/                   # Security overlays
│       ├── istio/                  # mTLS policies
│       └── gatekeeper/             # OPA constraints
│
├── gitops/                         # GitOps source of truth
│   ├── infrastructure/             # Flux-managed cluster infra
│   │   ├── addons/                 # EKS addons (ALB, EBS CSI, Autoscaler)
│   │   ├── clusters/               # Per-cluster bootstrap
│   │   ├── controllers/            # Flux + ArgoCD controllers
│   │   ├── networking/             # Ingress, Istio, Network Policies
│   │   ├── security/               # RBAC, IRSA, Pod Security
│   │   └── sources/                # Git and Helm repositories
│   ├── applications/               # ArgoCD-managed applications
│   │   ├── apps/                   # App bases (mlflow, kubeflow, kserve, monitoring, gpu-operator)
│   │   ├── environments/           # Per-environment overlays
│   │   └── projects/               # ArgoCD projects + ApplicationSet
│   ├── charts/                     # Helm charts
│   │   ├── mlflow/
│   │   ├── kserve/
│   │   ├── kubeflow-pipelines/
│   │   └── monitoring-stack/
│   ├── scripts/                    # Automation scripts
│   │   ├── install-gitops-controllers.sh
│   │   ├── package-helm-charts.sh  # Helm chart packaging
│   │   ├── promotion/              # Environment promotion (promote.py, notifications.py)
│   │   └── validation/             # Validation utilities
│   └── tests/                      # Property-based tests (8 test files)
│
├── ml-platform/                    # ML code and pipelines
│   ├── src/                        # Source code
│   │   ├── cli.py                  # Click CLI entry point
│   │   ├── main.py                 # Application entry point
│   │   ├── data/                   # Data loader, validator, feature engineering
│   │   ├── models/                 # Base model, classification, regression
│   │   ├── pipelines/              # Training pipeline, inference pipeline
│   │   ├── monitoring/             # Drift detector, metrics exporter, monitoring service
│   │   └── utils/                  # Logging, config manager
│   ├── tests/                      # Unit tests (test_cli, test_data, test_models, test_integration)
│   ├── pyproject.toml              # Poetry + setuptools dependencies
│   └── Dockerfile.monitoring       # Monitoring service Docker image
│
├── ci-cd/                          # CI/CD configurations
│   └── providers/
│       └── jenkins/                # Jenkinsfile
│
├── scripts/                        # Automation scripts
│   ├── bootstrap-terraform-backend.sh  # S3 + DynamoDB backend setup
│   └── setup-mlops-stack.sh        # MLOps tools installer
│
├── docs/                           # Documentation
│   ├── quick-start-guide.md
│   ├── ml-platform-guide.md
│   ├── model-monitoring-guide.md
│   ├── security-best-practices.md
│   ├── mlops-enterprise-recommendations.md
│   ├── PHASE2_IMPLEMENTATION_GUIDE.md
│   └── PENDING.md                  # Backlog & pending items
│
├── .github/workflows/             # GitHub Actions
│   ├── ci.yml                      # CI pipeline (Terraform, K8s, Python, Helm, Security)
│   └── environment-promotion.yml   # Dev → Staging → Production promotion
│
├── .circleci/                      # CircleCI config
├── .gitlab-ci.yml                  # GitLab CI config
├── Makefile                        # Main automation interface
├── README.md / README.es.md        # Main documentation
└── LICENSE                         # MIT License
```

---

## 4. Key Components

### 4.1 Infrastructure (Terraform)

**Modules** (reusable & tested with Go tests):

- **VPC**: Public/private subnets, NAT gateway, route tables
- **EKS**: Control plane, managed node groups, OIDC provider, IRSA roles
- **S3**: Raw data, curated data, model artifacts buckets with lifecycle policies (IA → Glacier)
- **ECR**: Trainer, inference, feature-transformer repos with vulnerability scanning
- **Glue**: Data catalogs, crawlers (scheduled daily), data quality rulesets

**Environments**:

- `dev`: Local Terraform backend (commented S3 backend config ready for migration)
- `staging`: Remote state with locking
- `prod`: Production-grade with strict access controls

**Key dev `main.tf` resources**:

- KMS key for encryption
- VPC module with configurable subnet counts
- EKS module with optional GPU node groups
- S3 buckets with lifecycle transitions
- ECR repos with scan-on-push
- Glue databases, crawlers, and data quality rules

### 4.2 ML Platform (Python)

**CLI Commands** (`mlops-train`):

- `train <data_path>`: End-to-end training with MLflow tracking
- `inference <data_path>`: Single/batch inference with health checks
- `validate <data_path>`: Data validation with Great Expectations
- `create-sample <output_path>`: Generate synthetic data

**Training Pipeline**:

1. Load data (CSV/Parquet/JSON from local or S3)
2. Validate data quality (Great Expectations suite)
3. Feature engineering (numeric/categorical preprocessing, feature selection)
4. Split data (train/val/test with stratification)
5. Train model (classification: RandomForest/XGBoost, regression: RandomForest)
6. Evaluate on test set
7. Save artifacts (model, feature pipeline, config) to MLflow

**Models**:

- `BaseModel`: Abstract class with MLflow integration, joblib serialization
- `ClassificationModel`: Binary/multiclass classification
- `RegressionModel`: Regression with cross-validation support

**Data Layer**:

- `DataLoader`: CSV/Parquet/JSON loading, S3 integration, synthetic data generation
- `DataValidator`: Great Expectations suites, validation reports
- `FeatureEngineer`: Preprocessing pipelines, feature selection (k-best, RFE)

### 4.3 Kubernetes Stack

**Namespaces**:

- `mlflow`: MLflow tracking server + PostgreSQL backend
- `kubeflow`: Kubeflow Pipelines UI (deployed via Helm chart in `gitops/charts/kubeflow-pipelines/`)
- `kserve`: KServe inference controller
- `monitoring`: Prometheus + Grafana + Alertmanager
- `istio-system`: Istio service mesh
- `gatekeeper-system`: OPA Gatekeeper

**Security**:

- Istio strict mTLS between MLOps services
- Gatekeeper constraints enforcing Pod Security Standards
- Network Policies limiting inter-namespace traffic
- External Secrets Operator for AWS Secrets Manager integration

**IRSA Roles** (created by `setup-mlops-stack.sh`):

- `mlops-{env}-mlflow-role`: S3 access for MLflow artifacts
- `mlops-{env}-kserve-role`: S3 read access for model serving

### 4.4 GitOps Architecture

**Flux v2** manages:

- Cluster infrastructure (addons, controllers)
- Networking (Istio, ingress)
- Security (RBAC, Pod Security Standards)
- Sources (Git repos, Helm repositories)

**ArgoCD** manages:

- MLOps applications (MLflow, Kubeflow, KServe, Monitoring)
- ApplicationSet for multi-environment deployments
- Projects with RBAC
- Notifications to Slack (`mlops-deployments`, `mlops-alerts` channels)

**Environment Promotion**:

- Automated via GitHub Actions (`environment-promotion.yml`)
- `develop` branch → auto PR to `staging`
- `staging` branch → auto PR to `main` (production)
- Manual approval required for production
- Promotion script: `gitops/scripts/promotion/promote.py`

### 4.5 Monitoring & Observability

**Metrics**:

- Prometheus scraping cluster and application metrics
- Grafana dashboards (cost estimation, model performance)
- ArgoCD Notifications for sync events

**Drift Detection** (`ml-platform/src/monitoring/`):

- `drift_detector.py`: Evidently-based data drift detection
- `model_monitor.py`: Model performance monitoring
- `monitoring_service.py`: HTTP service exposing drift reports
- `metrics_exporter.py`: Prometheus metrics exporter
- `run_drift_check.py`: Standalone drift check script
- Compares production data against reference dataset
- Containerized via `Dockerfile.monitoring`

**Health Checks**:

- All deployments have Kubernetes readiness/liveness probes
- Inference pipeline includes health check endpoint
- Monitoring service has HTTP health endpoint

---

## 5. CI/CD Pipelines

### GitHub Actions CI (`ci.yml`)

Triggered on push to `main`/`develop` and PRs to `main`:

| Job                  | Trigger                     | Description                                 |
| -------------------- | --------------------------- | ------------------------------------------- |
| `terraform-validate` | `infra/` changes            | `terraform fmt`, `init`, `validate`         |
| `terraform-test`     | `infra/` changes            | Go tests for VPC and S3 modules             |
| `k8s-validate`       | `k8s/` or `gitops/` changes | `kubectl --dry-run=client`, Kustomize build |
| `ml-platform-test`   | `ml-platform/` changes      | pytest, flake8, black                       |
| `security-scan`      | all changes                 | Trivy vulnerability scanner → SARIF upload  |
| `helm-lint`          | `gitops/charts/` changes    | `helm lint` + `helm template --debug`       |
| `mlops-validate`     | `scripts/` changes          | Bash script validation                      |

### Environment Promotion (`environment-promotion.yml`)

- Validates YAML syntax and GitOps checkpoints
- Runs property-based tests (Hypothesis)
- Creates PRs with detailed checklists
- Production promotions require explicit approval

---

## 6. Development Workflow

### Local Development (No Cloud)

```bash
cd ml-platform
poetry install -E dev
poetry run python -m src.cli create-sample data/sample.csv --n-samples 1000
poetry run python -m src.cli train data/sample.csv
poetry run python -m src.cli inference data/sample.csv --model-path artifacts/model_*.joblib
```

### AWS Deployment

```bash
# 1. Bootstrap backend (once per account)
./scripts/bootstrap-terraform-backend.sh dev us-west-2

# 2. Deploy infrastructure
make init ENV=dev
make plan ENV=dev
make apply ENV=dev

# 3. Install MLOps stack
make mlops-core        # MLflow + Monitoring
make mlops-full        # Full stack + Kubeflow + KServe

# 4. Access services
make port-forward-mlflow     # http://localhost:5000
make port-forward-grafana    # http://localhost:3000
make port-forward-kubeflow  # http://localhost:8080
```

---

## 7. Testing Strategy

### Infrastructure Tests

- **Go tests** (Terratest): VPC, EKS, S3, ECR, Glue modules
- **Terraform plan tests**: Syntax validation without AWS credentials

### ML Platform Tests

- **Unit tests**: Data loading, model training, feature engineering
- **Integration tests**: Full pipeline execution (require AWS/EKS)
- **Property-based tests**: Hypothesis for GitOps controller health

### GitOps Tests (8 test files)

- Controller health & replica readiness
- Repository structure conventions
- MLflow ArgoCD deployment consistency
- Promotion pipeline correctness
- Infrastructure reconciliation
- Application deployment consistency across environments

### Security Tests

- Trivy vulnerability scanning (SARIF output)
- `detect-secrets` pre-commit hook
- `.secrets.baseline` for secret auditing

---

## 8. Configuration Management

### Terraform Variables (`infra/environments/<env>/terraform.tfvars.example`)

- `aws_region`, `vpc_cidr`
- `node_group_instance_types`, `node_group_desired/max/min_size`
- `enable_gpu_node_group`, `gpu_node_group_*`
- `kubernetes_version`

### ML Platform Config

YAML-based configuration with environment overlays:

```yaml
data:
  source: "s3"
  s3_bucket: "my-ml-data"
  target_column: "label"
model:
  type: "classification"
  algorithm: "random_forest"
  hyperparameters:
    n_estimators: 100
mlflow:
  tracking_uri: "http://mlflow-server:5000"
  experiment_name: "production_models"
```

### Makefile Variables

- `ENV`: dev/staging/prod
- `CI_PROVIDER`: github/gitlab/circleci/jenkins
- `MLOPS_TOOLS`: comma-separated list (mlflow,kubeflow,kserve,monitoring)
- `REGION`: AWS region (default: us-west-2)

---

## 9. Security Implementation

| Layer                 | Implementation                                  |
| --------------------- | ----------------------------------------------- |
| Encryption at rest    | AWS KMS (S3, EBS, DynamoDB)                     |
| Encryption in transit | Istio mTLS (strict mode)                        |
| Secret management     | External Secrets Operator + AWS Secrets Manager |
| Container security    | ECR scan-on-push, Gatekeeper admission control  |
| Network security      | Network Policies, private EKS endpoint option   |
| IAM                   | IRSA roles with least-privilege policies        |
| Code security         | Pre-commit hooks, detect-secrets, Trivy scans   |
| Access control        | ArgoCD projects with RBAC                       |

---

## 10. Documentation Index

| Document        | Location                                   | Description                 |
| --------------- | ------------------------------------------ | --------------------------- |
| Quick Start     | `docs/quick-start-guide.md`                | 5-minute setup guide        |
| ML Platform     | `docs/ml-platform-guide.md`                | ML code details             |
| Monitoring      | `docs/model-monitoring-guide.md`           | Drift detection setup       |
| Security        | `docs/security-best-practices.md`          | mTLS, Gatekeeper guidelines |
| Enterprise Recs | `docs/mlops-enterprise-recommendations.md` | Production recommendations  |
| Phase 2 Guide   | `docs/PHASE2_IMPLEMENTATION_GUIDE.md`      | Implementation roadmap      |
| Pending Items   | `docs/PENDING.md`                          | Backlog & open items        |
| GitOps Setup    | `gitops/SETUP.md`                          | GitOps installation         |
| GitOps README   | `gitops/README.md`                         | GitOps architecture         |

---

## 11. Known Limitations & Pending Items

### Implemented ✅

- Flux v2 + ArgoCD controllers
- MLOps applications with multi-environment overlays
- External Secrets Operator
- ArgoCD Notifications (Slack)
- ApplicationSet for auto-generation
- Promotion pipeline (Python script + GitHub Actions + Jenkins)
- A/B Testing workflow templates (Argo Workflows)
- GPU Operator support (optional)

### Pending ⏳ (from `docs/PENDING.md`)

- Kubecost / OpenCost for real cost monitoring
- Feature Store with Feast (definitions, server, online/offline backends)
- ArgoCD Image Updater for automated image bumps
- End-to-end AWS test (Terraform → EKS → ArgoCD → MLflow → KServe)

---

## 12. Key Architectural Decisions

1. **Local-first development**: The `ml-platform/` works entirely locally with Poetry, no AWS required for ML experimentation.
2. **Modular Terraform**: Each AWS service has its own module with Go tests, enabling reuse across projects.
3. **Dual GitOps controllers**: Flux manages infrastructure (cluster-level), ArgoCD manages applications (app-level) — separation of concerns.
4. **Kustomize + Helm**: Raw K8s manifests use Kustomize for overlays; packaged apps use Helm charts in `gitops/charts/`.
5. **Joblib over pickle**: Model serialization uses joblib for better numpy/scipy object handling.
6. **Poetry for Python**: Dependency management uses Poetry (with pip fallback support via `pyproject.toml` setuptools backend).
7. **Multi-CI support**: Configurations for GitHub Actions, GitLab CI, CircleCI, and Jenkins are all maintained.

---

_This implementation overview was generated from repository analysis. Last updated: 2026-05-31. For the latest state, always refer to the actual source code and `docs/PENDING.md`._
