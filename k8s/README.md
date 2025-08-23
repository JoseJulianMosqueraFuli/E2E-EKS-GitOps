# Kubernetes Manifests

This directory contains Kubernetes manifests for deploying ML platform components.

## Structure

- `base/` - Base Kustomize configurations
- `overlays/` - Environment-specific overlays
- `charts/` - Helm charts for complex deployments
- `operators/` - Custom operator configurations

## Usage

1. Apply base manifests: `kubectl apply -k base/`
2. Apply environment overlay: `kubectl apply -k overlays/dev/`
3. Install Helm chart: `helm install mlflow charts/mlflow/`