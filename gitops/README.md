# GitOps Infrastructure

This directory contains the GitOps infrastructure setup for the MLOps platform using ArgoCD and Flux v2.

## Structure

```
gitops/
├── infrastructure/          # Flux-managed infrastructure
│   ├── controllers/        # GitOps controllers installation
│   ├── base/              # Base configurations
│   └── environments/      # Environment-specific configs
├── applications/          # ArgoCD-managed applications
│   ├── projects/          # ArgoCD projects
│   ├── apps/             # Application definitions
│   └── overlays/         # Environment overlays
├── charts/               # Helm charts for MLOps components
├── scripts/              # Installation and management scripts
└── tests/               # Property-based and unit tests
```

## Quick Start

1. Install GitOps controllers:

   ```bash
   ./scripts/install-gitops-controllers.sh
   ```

2. Configure repositories:

   ```bash
   ./scripts/setup-repositories.sh
   ```

3. Deploy applications:
   ```bash
   ./scripts/deploy-applications.sh
   ```

## Components

- **ArgoCD**: Application deployment and management
- **Flux v2**: Infrastructure and configuration management
- **External Secrets Operator**: Secret management
- **ArgoCD Image Updater**: Automated image updates
