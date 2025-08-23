# MLOps End-to-End Platform on EKS with GitOps

A complete MLOps pipeline implementation on Amazon EKS that provides end-to-end automation from raw data ingestion to model serving with canary deployments, leveraging GitOps principles for infrastructure and application management.

## Architecture Overview

This platform demonstrates enterprise-ready MLOps practices combining AWS services, Kubernetes, and MLOps tooling to create a reusable foundation for ML teams. The system provides:

- **Reproducible ML workflows** with automatic experiment tracking
- **Automated canary deployments** with performance-based rollbacks  
- **GitOps-managed infrastructure** with version-controlled changes
- **Comprehensive security controls** and minimal privilege access
- **End-to-end observability** with SLO monitoring and alerting

## Repository Structure

```
├── infra/                  # Terraform infrastructure code
│   ├── modules/           # Reusable Terraform modules
│   │   ├── vpc/          # VPC and networking
│   │   ├── eks/          # EKS cluster configuration
│   │   └── s3/           # S3 buckets for data storage
│   └── environments/     # Environment-specific configurations
│       └── dev/          # Development environment
├── apps/                  # Application code
│   ├── trainer/          # ML training application
│   └── inference/        # ML inference service
├── workflows/             # Argo Workflow templates
├── k8s/                  # Kubernetes manifests
├── ops/                  # Operational tools and monitoring
└── .github/workflows/    # CI/CD pipeline definitions
```

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0
- kubectl
- Docker
- Python 3.9+

### 1. Deploy Infrastructure

```bash
# Navigate to development environment
cd infra/environments/dev

# Copy and customize variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your specific values

# Initialize and deploy
terraform init
terraform plan
terraform apply
```

### 2. Configure kubectl

```bash
# Update kubeconfig for the new EKS cluster
aws eks update-kubeconfig --region us-west-2 --name mlops-dev-cluster
```

### 3. Deploy Platform Components

```bash
# Deploy base Kubernetes applications
kubectl apply -k k8s/base/

# Deploy development overlay
kubectl apply -k k8s/overlays/dev/
```

### 4. Deploy ML Workflows

```bash
# Deploy Argo Workflow templates
kubectl apply -f workflows/templates/ -n argo
```

## Key Components

### Infrastructure (Terraform)

- **VPC Module**: Multi-AZ VPC with public/private subnets and NAT gateways
- **EKS Module**: Managed Kubernetes cluster with IRSA configuration
- **S3 Module**: Encrypted buckets for raw data, curated data, and model artifacts

### Applications

- **Trainer**: Containerized ML training application with MLflow integration
- **Inference**: FastAPI-based model serving with health checks and metrics

### Platform Services

- **MLflow**: Experiment tracking and model registry
- **Argo CD**: GitOps continuous deployment
- **Argo Workflows**: ML pipeline orchestration
- **KServe**: Model serving with canary deployments
- **Prometheus/Grafana**: Monitoring and observability

## Development Workflow

1. **Data Ingestion**: Raw data uploaded to S3 triggers validation pipeline
2. **Data Validation**: Great Expectations validates data quality
3. **Feature Engineering**: Automated feature transformation and storage
4. **Model Training**: MLflow tracks experiments and registers models
5. **Model Deployment**: KServe deploys models with canary configuration
6. **Monitoring**: Prometheus collects metrics for SLO monitoring

## Security Features

- **Encryption at Rest**: KMS encryption for S3 and EKS secrets
- **IRSA**: IAM Roles for Service Accounts for secure AWS access
- **Network Security**: Private subnets and security groups
- **Container Scanning**: Trivy vulnerability scanning in CI/CD
- **Policy Enforcement**: OPA Gatekeeper for Kubernetes policies

## Monitoring and Observability

- **System Metrics**: CPU, memory, network, and storage metrics
- **Application Metrics**: Request latency, throughput, and error rates
- **ML Metrics**: Model drift, prediction accuracy, and data quality
- **SLO Monitoring**: Automated alerting on threshold breaches

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support, please open an issue in the GitHub repository.