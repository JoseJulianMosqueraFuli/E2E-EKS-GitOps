# Infrastructure Base

This directory contains base infrastructure configurations that are shared across all environments.

## Structure

```
base/
├── README.md
├── cluster-addons/          # AWS cluster addons (ALB, EBS CSI, etc.)
├── networking/              # Istio, ingress controllers
└── common/                  # Common configurations
```

## Usage

Base configurations are referenced by environment-specific overlays in the `clusters/` directory.

## Components

### Cluster Addons

- AWS Load Balancer Controller
- EBS CSI Driver
- Cluster Autoscaler

### Networking

- Istio Service Mesh
- Ingress Controllers
- Network Policies

### Common

- Shared ConfigMaps
- Common Labels and Annotations
