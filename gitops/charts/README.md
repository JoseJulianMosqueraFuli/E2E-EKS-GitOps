# MLOps Helm Charts

This directory contains Helm charts for MLOps platform components, designed for GitOps deployment with ArgoCD.

## Available Charts

| Chart                  | Version | App Version | Description                                                            |
| ---------------------- | ------- | ----------- | ---------------------------------------------------------------------- |
| **mlflow**             | 1.0.0   | 2.8.1       | MLflow tracking server with PostgreSQL backend and S3 artifact storage |
| **kubeflow-pipelines** | 1.0.0   | 2.0.1       | Kubeflow Pipelines for ML workflow orchestration                       |
| **kserve**             | 1.0.0   | 0.11.0      | KServe model serving platform for Kubernetes                           |
| **monitoring-stack**   | 1.0.0   | 1.0.0       | MLOps monitoring with Prometheus, Grafana, and Evidently               |

## Chart Repository

Charts are packaged and served through a Helm repository for ArgoCD consumption.

### Repository URL

```
https://org.github.io/mlops-helm-charts
```

### Adding the Repository

```bash
# Add the MLOps Helm repository
helm repo add mlops-charts https://org.github.io/mlops-helm-charts
helm repo update

# Search available charts
helm search repo mlops-charts
```

## Usage

### Package Charts

```bash
# Package individual charts
helm package mlflow
helm package kserve
helm package kubeflow-pipelines
helm package monitoring-stack

# Update repository index
helm repo index . --url https://org.github.io/mlops-helm-charts
```

### Install via Helm CLI

```bash
# Install MLflow
helm install mlflow mlops-charts/mlflow \
  --namespace mlflow \
  --create-namespace \
  --values mlflow/values-production.yaml

# Install KServe
helm install kserve mlops-charts/kserve \
  --namespace kserve-system \
  --create-namespace

# Install Kubeflow Pipelines
helm install kubeflow mlops-charts/kubeflow-pipelines \
  --namespace kubeflow \
  --create-namespace

# Install Monitoring Stack
helm install monitoring mlops-charts/monitoring-stack \
  --namespace monitoring \
  --create-namespace
```

### Install via ArgoCD

Charts are automatically referenced in ArgoCD Application definitions. See `gitops/applications/projects/mlops-helm-repository.yaml` for ArgoCD integration.

## Chart Structure

Each chart follows the standard Helm chart structure:

```
chart-name/
├── Chart.yaml           # Chart metadata and dependencies
├── values.yaml          # Default configuration values
├── templates/
│   ├── _helpers.tpl     # Template helpers
│   ├── deployment.yaml  # Kubernetes Deployment
│   ├── service.yaml     # Kubernetes Service
│   ├── configmap.yaml   # ConfigMaps
│   ├── serviceaccount.yaml
│   ├── rbac.yaml        # RBAC resources
│   └── ...
└── README.md            # Chart documentation
```

## Chart Dependencies

| Chart              | Dependencies                    |
| ------------------ | ------------------------------- |
| mlflow             | postgresql (Bitnami)            |
| kubeflow-pipelines | mysql, minio (Bitnami)          |
| kserve             | cert-manager (Jetstack)         |
| monitoring-stack   | prometheus, grafana (Community) |

### Update Dependencies

```bash
# Update dependencies for a specific chart
cd mlflow && helm dependency update

# Update all chart dependencies
for chart in mlflow kserve kubeflow-pipelines monitoring-stack; do
  cd $chart && helm dependency update && cd ..
done
```

## Environment-Specific Values

Create environment-specific value files for different deployments:

```
chart-name/
├── values.yaml              # Default values
├── values-dev.yaml          # Development environment
├── values-staging.yaml      # Staging environment
└── values-production.yaml   # Production environment
```

### Example: MLflow Production Values

```yaml
# values-production.yaml
mlflow:
  replicaCount: 3
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

postgresql:
  primary:
    persistence:
      size: 100Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10

podDisruptionBudget:
  enabled: true
  minAvailable: 2
```

## Versioning

Charts follow semantic versioning:

- **MAJOR**: Breaking changes to values or templates
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

## Testing Charts

```bash
# Lint a chart
helm lint mlflow

# Template rendering (dry-run)
helm template mlflow mlflow/ --debug

# Install with dry-run
helm install mlflow mlflow/ --dry-run --debug
```

## ArgoCD Integration

The charts are integrated with ArgoCD through:

1. **HelmRepository** resource in Flux (for infrastructure)
2. **ArgoCD Application** resources for each MLOps component
3. **ApplicationSet** for multi-environment deployments

See `gitops/applications/projects/mlops-helm-repository.yaml` for complete ArgoCD configuration.
