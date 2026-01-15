# ArgoCD Applications

This directory contains ArgoCD application definitions for the MLOps platform.

## Structure

```
applications/
├── projects/              # ArgoCD project definitions
├── apps/                 # Application manifests
│   ├── mlflow/
│   ├── kubeflow/
│   ├── kserve/
│   └── monitoring/
└── environments/         # Environment-specific configurations
    ├── dev/
    ├── staging/
    └── production/
```

## Usage

Applications are automatically synced by ArgoCD when changes are committed to this repository.

### Creating a New Application

1. Create application directory in `apps/`
2. Add base manifests
3. Create environment overlays in `environments/`
4. Define ArgoCD Application in the appropriate environment directory
