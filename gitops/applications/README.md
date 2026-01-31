# ArgoCD Applications

This directory contains ArgoCD application definitions for the MLOps platform.

## Structure

```
applications/
├── projects/                    # ArgoCD project definitions
│   ├── mlops-core.yaml         # Core MLOps project with RBAC
│   └── mlops-applicationset.yaml # ApplicationSet for automated app generation
├── apps/                        # Application manifests (Kustomize)
│   ├── mlflow/
│   │   ├── base/               # Base manifests
│   │   └── overlays/           # Environment-specific overlays
│   │       ├── dev/
│   │       ├── staging/
│   │       └── production/
│   ├── kubeflow/
│   │   ├── base/
│   │   └── overlays/
│   ├── kserve/
│   │   ├── base/
│   │   └── overlays/
│   └── monitoring/
│       ├── base/
│       └── overlays/
└── environments/                # Environment-specific ArgoCD Applications
    ├── dev/
    │   ├── kustomization.yaml
    │   ├── mlflow-application.yaml
    │   ├── kubeflow-application.yaml
    │   ├── kserve-application.yaml
    │   └── monitoring-application.yaml
    ├── staging/
    │   ├── kustomization.yaml
    │   ├── mlflow-application.yaml
    │   ├── kubeflow-application.yaml
    │   ├── kserve-application.yaml
    │   └── monitoring-application.yaml
    └── production/
        ├── kustomization.yaml
        ├── mlflow-application.yaml
        ├── kubeflow-application.yaml
        ├── kserve-application.yaml
        └── monitoring-application.yaml
```

## MLOps Applications

| Application | Description                               | Namespace  |
| ----------- | ----------------------------------------- | ---------- |
| MLflow      | ML experiment tracking and model registry | mlflow     |
| Kubeflow    | ML pipeline orchestration                 | kubeflow   |
| KServe      | Model serving and inference               | kserve     |
| Monitoring  | Prometheus, Grafana observability stack   | monitoring |

## Environment Configuration

### Dev Environment

- Branch: `develop`
- Auto-sync: Enabled with pruning
- Revision history: 5 versions
- Resources: Minimal for cost optimization

### Staging Environment

- Branch: `staging`
- Auto-sync: Enabled with pruning
- Revision history: 10 versions
- Resources: Moderate for testing

### Production Environment

- Branch: `main`
- Auto-sync: Enabled without pruning (manual prune required)
- Revision history: 15 versions
- Resources: Full production capacity
- Slack notifications enabled

## Usage

### Deploy to a Specific Environment

```bash
# Apply dev environment applications
kubectl apply -k environments/dev/

# Apply staging environment applications
kubectl apply -k environments/staging/

# Apply production environment applications
kubectl apply -k environments/production/
```

### Using ApplicationSet (Recommended)

The ApplicationSet automatically generates applications for all environments:

```bash
kubectl apply -f projects/mlops-applicationset.yaml
```

### Creating a New Application

1. Create application directory in `apps/<app-name>/`
2. Add base manifests in `apps/<app-name>/base/`
3. Create environment overlays in `apps/<app-name>/overlays/<env>/`
4. Add ArgoCD Application in `environments/<env>/<app-name>-application.yaml`
5. Update the environment's `kustomization.yaml` to include the new application

### Sync Policies

| Environment | Auto-Sync | Self-Heal | Prune | Retry Limit |
| ----------- | --------- | --------- | ----- | ----------- |
| Dev         | Yes       | Yes       | Yes   | 5           |
| Staging     | Yes       | Yes       | Yes   | 5           |
| Production  | Yes       | Yes       | No    | 3           |

## RBAC Roles

- **mlops-admin**: Full access to all MLOps applications
- **mlops-developer**: Read and sync access to applications

## Notifications

Production applications are configured with Slack notifications:

- `mlops-deployments`: Successful sync notifications
- `mlops-alerts`: Failed sync notifications
