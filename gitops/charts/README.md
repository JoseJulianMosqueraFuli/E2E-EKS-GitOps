# MLOps Helm Charts

This directory contains Helm charts for MLOps platform components.

## Available Charts

- **mlflow**: MLflow tracking server with PostgreSQL and MinIO
- **kubeflow-pipelines**: Kubeflow Pipelines orchestration
- **kserve**: KServe model serving platform
- **monitoring-stack**: Prometheus, Grafana, and Evidently monitoring

## Chart Repository

Charts are packaged and served through a Helm repository for ArgoCD consumption.

## Usage

```bash
# Package a chart
helm package charts/mlflow

# Update repository index
helm repo index .

# Install via ArgoCD
# Charts are automatically referenced in ArgoCD Application definitions
```

## Chart Structure

Each chart follows the standard Helm chart structure:

```
chart-name/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ...
└── README.md
```
