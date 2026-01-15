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
│   ├── projects/          # ArgoCD projects
│   │   └── mlops-core.yaml
│   ├── apps/             # Application definitions (to be added)
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
pytest -m property
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

### To Be Added (Subsequent Tasks)

- ⏳ **MLOps Applications**: MLflow, Kubeflow, KServe, Monitoring
- ⏳ **External Secrets Operator**: Secure secret management
- ⏳ **ArgoCD Image Updater**: Automated image updates
- ⏳ **Multi-Environment Promotion**: Automated promotion pipelines
- ⏳ **Monitoring & Alerting**: GitOps operations monitoring

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

1. **Task 2**: Create repository structure and organization
2. **Task 3**: Implement MLOps application management with ArgoCD
3. **Task 4**: Implement infrastructure management with Flux
4. **Task 5**: Validate core GitOps functionality

See [.kiro/specs/gitops-implementation/tasks.md](../.kiro/specs/gitops-implementation/tasks.md) for the complete implementation plan.
