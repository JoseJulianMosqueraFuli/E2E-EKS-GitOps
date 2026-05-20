# GitOps Infrastructure

This directory contains the GitOps infrastructure setup for the MLOps platform using ArgoCD and Flux v2.

## Overview

The GitOps implementation provides:

- **Declarative Infrastructure**: All infrastructure and applications defined in Git
- **Automated Deployments**: Changes in Git automatically applied to clusters
- **Multi-Environment Support**: Separate configurations for dev, staging, and production
- **Audit Trail**: Complete history of all changes through Git commits
- **Disaster Recovery**: Cluster can be rebuilt from Git repository

## Structure

```
gitops/
├── infrastructure/          # Flux-managed infrastructure
│   ├── controllers/        # GitOps controllers (Flux, ArgoCD)
│   │   ├── flux-system/   # Flux v2 controllers
│   │   └── argocd/        # ArgoCD controllers
│   ├── base/              # Base configurations
│   └── environments/      # Environment-specific configs
│       ├── dev/
│       ├── staging/
│       └── production/
├── applications/          # ArgoCD-managed applications
│   ├── projects/          # ArgoCD projects + ApplicationSet
│   │   ├── mlops-core.yaml
│   │   ├── mlops-applicationset.yaml
│   │   └── mlops-helm-repository.yaml
│   ├── apps/             # Application bases + overlays
│   │   ├── mlflow/
│   │   ├── kubeflow/
│   │   ├── kserve/
│   │   ├── monitoring/    # Includes Alertmanager + ArgoCD Notifications
│   │   └── gpu-operator/  # Optional NVIDIA GPU Operator
│   └── environments/     # Environment overlays
│       ├── dev/
│       ├── staging/
│       └── production/
├── charts/               # Helm charts for MLOps components
├── scripts/              # Installation and management scripts
│   └── install-gitops-controllers.sh
└── tests/               # Property-based and unit tests
    ├── test_gitops_controller_health.py
    └── requirements.txt
```

## Quick Start

### 0. Install Dependencies (Poetry)

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Or use pip (alternative)
pip install -r tests/requirements.txt
```

### 1. Install GitOps Controllers

```bash
cd scripts
./install-gitops-controllers.sh
```

This installs:

- Flux v2 controllers (source, kustomize, helm, notification)
- ArgoCD controllers (server, repo-server, application-controller)

### 2. Verify Installation

```bash
# Check Flux
kubectl get pods -n flux-system

# Check ArgoCD
kubectl get pods -n argocd

# Run property-based tests
cd ../tests
./setup_test_env.sh
poetry run pytest -m property
```

### 3. Access ArgoCD UI

```bash
# Get admin password
./install-gitops-controllers.sh password

# Port-forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
# Username: admin
# Password: (from previous command)
```

## Components

### Installed

- ✅ **Flux v2**: Infrastructure and configuration management
- ✅ **ArgoCD**: Application deployment and management
- ✅ **Repository Structure**: Organized for multi-environment deployments
- ✅ **Property-Based Tests**: Automated testing for controller health
- ✅ **MLOps Applications**: MLflow, Kubeflow, KServe, Monitoring (dev/staging/production overlays)
- ✅ **External Secrets Operator**: Secure secret management for MLflow and other components
- ✅ **ArgoCD Notifications**: Slack notifications for sync events (`mlops-deployments`, `mlops-alerts`)
- ✅ **ApplicationSet**: Auto-generates applications across environments
- ✅ **Promotion Pipeline**: `scripts/promote.py` + GitHub Actions + Jenkins for env-to-env promotion
- ✅ **A/B Testing Workflow**: Argo Workflows template for model A/B experiments

### Pending

See [docs/PENDING.md](../docs/PENDING.md) for the authoritative status. Key open items:

- ⏳ **Kubecost / OpenCost**: Replace estimated cost dashboard with a real exporter
- ⏳ **Feature Store with Feast**: Feature definitions, server, and online/offline backends
- ⏳ **ArgoCD Image Updater**: Automated image bumps from registry
- ⏳ **End-to-end test on AWS**: Full Terraform → EKS → ArgoCD → MLflow → KServe validation

## Documentation

- [SETUP.md](SETUP.md) - Detailed setup guide
- [tests/README.md](tests/README.md) - Testing documentation
- [applications/README.md](applications/README.md) - Application management guide

## Testing

Property-based tests verify GitOps controller health:

```bash
cd tests

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run only property tests
pytest -m property

# Run with verbose output
pytest -v
```

Tests validate:

- Controller deployments are healthy
- All required replicas are ready
- Health status remains stable over time
- Namespaces exist and are properly configured

## Next Steps

After completing this foundation:

1. Review [docs/PENDING.md](../docs/PENDING.md) for the current backlog
2. Run an end-to-end test on a real EKS cluster (Terraform → ArgoCD → MLflow → KServe)
3. Wire ArgoCD Image Updater for automated image bumps
4. Replace the estimated cost dashboard with Kubecost / OpenCost
