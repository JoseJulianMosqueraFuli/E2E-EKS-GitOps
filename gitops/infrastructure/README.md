# GitOps Infrastructure Repository

This directory contains Flux-managed infrastructure configurations for the MLOps platform.

## Repository Structure

```
infrastructure/
├── clusters/                    # Environment-specific cluster configurations
│   ├── dev/
│   │   ├── flux-system/        # Flux bootstrap configuration
│   │   ├── infrastructure/     # Infrastructure overlays
│   │   └── config/             # Cluster-specific config
│   ├── staging/
│   └── production/
├── controllers/                 # GitOps controller deployments
│   ├── flux-system/            # Flux v2 controllers
│   └── argocd/                 # ArgoCD installation
├── sources/                     # Flux source definitions
│   ├── git-repository.yaml     # Git repository sources
│   └── helm-repository.yaml    # Helm repository sources
├── flux-config/                 # Flux Kustomization resources
│   └── infrastructure-kustomization.yaml
├── environments/                # Legacy environment configs
├── base/                        # Shared base configurations
└── security/                    # Security policies and RBAC
```

## Environment Configuration

### Development (dev)

- Sync interval: 1 minute
- Branch: `dev`
- Monitoring: Enabled
- Backup: Disabled
- Log level: Debug

### Staging

- Sync interval: 5 minutes
- Branch: `staging`
- Monitoring: Enabled
- Backup: Enabled
- Log level: Info

### Production

- Sync interval: 10 minutes
- Branch: `main`
- Monitoring: Enabled
- Backup: Enabled
- Log level: Warn

## Flux Source Controllers

### Git Repositories

- `infrastructure-repo`: Infrastructure configurations
- `applications-repo`: ArgoCD application manifests
- `helm-charts-repo`: MLOps Helm charts

### Helm Repositories

- `mlops-charts`: Custom MLOps Helm charts
- `bitnami`: Bitnami charts for dependencies
- `prometheus-community`: Monitoring stack
- `grafana`: Grafana dashboards

## Bootstrap Process

1. Install Flux CLI:

   ```bash
   curl -s https://fluxcd.io/install.sh | sudo bash
   ```

2. Bootstrap Flux for an environment:

   ```bash
   flux bootstrap github \
     --owner=org \
     --repository=gitops-infrastructure \
     --branch=main \
     --path=./infrastructure/clusters/production \
     --personal
   ```

3. Verify installation:
   ```bash
   flux check
   flux get all
   ```

## Reconciliation

Flux automatically reconciles the cluster state with the Git repository:

- **Source Controller**: Fetches Git/Helm repositories
- **Kustomize Controller**: Applies Kustomize configurations
- **Helm Controller**: Manages Helm releases
- **Notification Controller**: Sends deployment notifications

## Health Checks

Each Kustomization includes health checks to ensure deployments are successful:

```yaml
healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: source-controller
    namespace: flux-system
```

## Troubleshooting

Check Flux status:

```bash
flux get sources git
flux get kustomizations
flux logs
```

Force reconciliation:

```bash
flux reconcile source git flux-system
flux reconcile kustomization flux-system
```
