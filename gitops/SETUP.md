# GitOps Infrastructure Setup Guide

This guide walks through setting up the complete GitOps infrastructure for the MLOps platform.

## Overview

The GitOps implementation uses:

- **Flux v2** for infrastructure management
- **ArgoCD** for application management
- **External Secrets Operator** for secret management (to be added)
- **ArgoCD Image Updater** for automated image updates (to be added)

## Prerequisites

Before starting, ensure you have:

1. **Kubernetes Cluster**: EKS cluster running and accessible
2. **kubectl**: Configured to access your cluster
3. **helm**: Version 3.0 or higher
4. **Git**: For repository management
5. **AWS CLI**: Configured with appropriate credentials

```bash
# Verify prerequisites
kubectl cluster-info
helm version
git --version
aws sts get-caller-identity
```

## Installation Steps

### Step 1: Install GitOps Controllers

Install Flux v2 and ArgoCD controllers:

```bash
cd gitops/scripts
./install-gitops-controllers.sh
```

This script will:

1. Install Flux v2 controllers (source, kustomize, helm, notification)
2. Install ArgoCD controllers (server, repo-server, application-controller)
3. Configure initial Git repository connections
4. Verify all controllers are healthy

### Step 2: Access ArgoCD UI

Get the ArgoCD admin password:

```bash
./install-gitops-controllers.sh password
```

Port-forward to access the UI:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Access at: https://localhost:8080

- Username: `admin`
- Password: (from previous command)

### Step 3: Configure Git Repositories

The installation script automatically configures the infrastructure repository. To add additional repositories:

```bash
# For Flux (infrastructure)
kubectl apply -f - <<EOF
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-infra-repo
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/org/my-infra-repo
  ref:
    branch: main
EOF

# For ArgoCD (applications)
# Use ArgoCD UI or CLI to add repositories
argocd repo add https://github.com/org/my-app-repo
```

### Step 4: Deploy MLOps Applications

Applications will be deployed in subsequent tasks. The structure is ready for:

- MLflow
- Kubeflow Pipelines
- KServe
- Monitoring Stack

## Repository Structure

```
gitops/
├── infrastructure/          # Flux-managed infrastructure
│   ├── controllers/        # GitOps controllers
│   ├── base/              # Base configurations
│   └── environments/      # Environment-specific configs
│       ├── dev/
│       ├── staging/
│       └── production/
├── applications/          # ArgoCD-managed applications
│   ├── projects/          # ArgoCD projects
│   ├── apps/             # Application definitions
│   └── environments/     # Environment overlays
│       ├── dev/
│       ├── staging/
│       └── production/
├── charts/               # Helm charts
├── scripts/              # Installation scripts
└── tests/               # Property-based and unit tests
```

## Verification

### Verify Flux Controllers

```bash
kubectl get pods -n flux-system
kubectl get gitrepositories -n flux-system
kubectl get kustomizations -n flux-system
```

All pods should be in `Running` state.

### Verify ArgoCD Controllers

```bash
kubectl get pods -n argocd
kubectl get applications -n argocd
```

All pods should be in `Running` state.

### Run Property-Based Tests

```bash
cd gitops/tests
./setup_test_env.sh
pytest -m property
```

Tests verify:

- All controllers are healthy
- Namespaces exist
- Deployments have correct replica counts
- Health status is stable over time

## Troubleshooting

### Controllers Not Starting

Check logs:

```bash
# Flux controllers
kubectl logs -n flux-system deployment/source-controller
kubectl logs -n flux-system deployment/kustomize-controller

# ArgoCD controllers
kubectl logs -n argocd deployment/argocd-server
kubectl logs -n argocd deployment/argocd-application-controller
```

### Git Repository Connection Issues

Check Git repository status:

```bash
kubectl get gitrepositories -n flux-system
kubectl describe gitrepository infrastructure-repo -n flux-system
```

### ArgoCD Sync Issues

Check application status:

```bash
kubectl get applications -n argocd
argocd app get <app-name>
argocd app sync <app-name>
```

## Next Steps

After completing this setup:

1. **Configure Secret Management**: Deploy External Secrets Operator
2. **Deploy MLOps Applications**: MLflow, Kubeflow, KServe
3. **Setup Image Automation**: Configure ArgoCD Image Updater
4. **Configure Monitoring**: Deploy Prometheus and Grafana for GitOps metrics
5. **Setup Multi-Environment Promotion**: Configure promotion pipelines

## Security Considerations

1. **RBAC**: Controllers run with minimal required permissions
2. **Network Policies**: To be configured in later tasks
3. **Secret Management**: Use External Secrets Operator (not plain Kubernetes secrets)
4. **Git Authentication**: Use SSH keys or deploy tokens (not personal credentials)
5. **TLS**: ArgoCD UI uses TLS by default

## Maintenance

### Updating Controllers

```bash
# Update Flux
kubectl apply -k gitops/infrastructure/controllers/flux-system

# Update ArgoCD
kubectl apply -k gitops/infrastructure/controllers/argocd
```

### Backup and Recovery

Backup ArgoCD configurations:

```bash
kubectl get applications -n argocd -o yaml > argocd-apps-backup.yaml
kubectl get appprojects -n argocd -o yaml > argocd-projects-backup.yaml
```

Backup Flux configurations:

```bash
kubectl get gitrepositories -n flux-system -o yaml > flux-repos-backup.yaml
kubectl get kustomizations -n flux-system -o yaml > flux-kustomizations-backup.yaml
```

## Resources

- [Flux Documentation](https://fluxcd.io/docs/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [GitOps Principles](https://opengitops.dev/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
