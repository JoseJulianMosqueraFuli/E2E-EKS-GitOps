# ArgoCD Applications

This directory contains the ArgoCD application definitions for the MLOps platform.

The single source of truth for Kubernetes manifests is `gitops/applications/apps/<app>/base/`.
The legacy entrypoints under `k8s/mlops-stack/` and `k8s/security/` still exist as thin `kustomization.yaml` pointers to these bases for backwards compatibility, but new work should happen here.

## Structure

```
applications/
├── projects/                    # ArgoCD project definitions
│   ├── mlops-core.yaml         # Core MLOps project with RBAC
│   └── mlops-applicationset.yaml # ApplicationSet for automated app generation
└── apps/                        # Application manifests (Kustomize)
    ├── mlflow/
    │   ├── base/               # Base manifests
    │   └── overlays/           # Environment-specific overlays
    │       ├── dev/
    │       ├── staging/
    │       └── production/
    ├── kubeflow/
    │   ├── base/
    │   └── overlays/
    ├── kserve/
    │   ├── base/
    │   └── overlays/
    ├── monitoring/
    │   ├── base/
    │   └── overlays/
    ├── argo-workflows/
    │   ├── base/
    │   └── overlays/
    ├── feast/
    │   ├── base/
    │   └── overlays/
    ├── external-secrets/
    │   ├── base/
    │   └── overlays/
    ├── gatekeeper/
    │   ├── base/
    │   └── overlays/
    └── istio/
        ├── base/
        └── overlays/
```

## MLOps Applications

| Application      | Description                               | Namespace          |
| ---------------- | ----------------------------------------- | ------------------ |
| MLflow           | ML experiment tracking and model registry | mlflow             |
| Kubeflow         | ML pipeline orchestration                 | kubeflow           |
| KServe           | Model serving and inference               | kserve             |
| Monitoring       | Prometheus, Grafana observability stack   | monitoring         |
| Argo Workflows   | ML workflow engine and A/B testing        | argo-workflows     |
| Feast            | Feature store (local Redis backend)       | feast              |
| External Secrets | AWS Secrets Manager integration           | external-secrets   |
| Gatekeeper       | OPA/Gatekeeper policy enforcement         | gatekeeper-system  |
| Istio            | Service mesh mTLS and authorization       | istio-system       |

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

### Deploy with ApplicationSet (Recommended)

The `mlops-applicationset.yaml` automatically generates all applications for every environment:

```bash
kubectl apply -f projects/mlops-applicationset.yaml
```

After applying, ArgoCD creates one `Application` per app/environment combination:

```bash
kubectl get applications -n argocd
```

### Deploy a single overlay manually

If you need to apply one app/environment overlay directly (for testing or debugging):

```bash
kubectl apply -k apps/mlflow/overlays/dev/
```

### Creating a New Application

1. Create application directory in `apps/<app-name>/`
2. Add base manifests in `apps/<app-name>/base/`
3. Create environment overlays in `apps/<app-name>/overlays/<env>/`
4. Add the app to `projects/mlops-applicationset.yaml`

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
