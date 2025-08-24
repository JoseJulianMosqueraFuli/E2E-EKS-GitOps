# 🚀 Enterprise MLOps Platform on EKS with GitOps

A production-ready, enterprise-grade MLOps platform built on Amazon EKS with GitOps principles, featuring automated ML pipelines, model serving, and comprehensive infrastructure as code.

## 🎯 Features

### 🏗️ **Infrastructure as Code**
- **Terraform modules** for AWS resources (VPC, EKS, S3, ECR, Glue)
- **Multi-environment support** (dev, staging, prod)
- **Security-first design** with IRSA, VPC endpoints, and KMS encryption
- **Comprehensive testing** with Terratest (Go)

### 🤖 **MLOps Stack**
- **MLflow** - Experiment tracking and model registry
- **Kubeflow Pipelines** - ML workflow orchestration
- **Seldon Core** - Production model serving
- **Prometheus + Grafana** - Monitoring and observability
- **AWS Glue** - Data catalog and ETL

### 🔄 **CI/CD Flexibility**
- **GitHub Actions** (default)
- **GitLab CI** 
- **CircleCI**
- **Jenkins** support
- **Modular configuration** - easily switch between providers

### 🛡️ **Enterprise Security**
- **IRSA** (IAM Roles for Service Accounts)
- **VPC endpoints** for private AWS service access
- **KMS encryption** for all data at rest
- **Network policies** and security groups
- **Container image scanning**

## 🚀 Quick Start

### Prerequisites
```bash
# Install required tools
brew install terraform kubectl helm aws-cli go

# Or using package managers
# Ubuntu/Debian: apt-get install terraform kubectl helm awscli golang
# CentOS/RHEL: yum install terraform kubectl helm awscli golang

# Configure AWS credentials
aws configure
```

### 1. Deploy Infrastructure
```bash
# Clone and setup
git clone <repository-url>
cd mlops-e2e-eks-gitops

# Quick start for development
make quickstart-dev

# Or step by step
make init ENV=dev
make plan ENV=dev
make apply ENV=dev
```

### 2. Deploy MLOps Stack
```bash
# Install core MLOps tools (MLflow + Monitoring)
make mlops-core

# Or install full stack (MLflow + Kubeflow + Seldon + Monitoring)
make mlops-full

# Or install specific tools
make mlops-mlflow-only
make mlops-monitoring-only
```

### 3. Access Services
```bash
# MLflow UI
make port-forward-mlflow
# Open http://localhost:5000

# Grafana Dashboard
make port-forward-grafana  
# Open http://localhost:3000 (admin/admin123)

# Kubeflow Pipelines
make port-forward-kubeflow
# Open http://localhost:8080
```

## 📁 Project Structure

```
├── 🏗️ infra/                     # Infrastructure as Code
│   ├── modules/                  # Reusable Terraform modules
│   │   ├── vpc/                 # VPC with security groups & endpoints
│   │   ├── eks/                 # EKS with IRSA & autoscaling
│   │   ├── s3/                  # S3 buckets with encryption
│   │   ├── ecr/                 # Container registry
│   │   └── glue/                # Data catalog
│   └── environments/            # Environment configurations
│       ├── dev/
│       ├── staging/
│       └── prod/
├── ☸️ k8s/                       # Kubernetes Manifests
│   └── mlops-stack/             # MLOps tools
│       ├── mlflow/              # Experiment tracking
│       ├── kubeflow/            # ML pipelines
│       ├── seldon/              # Model serving
│       └── monitoring/          # Prometheus & Grafana
├── 🤖 ml-platform/               # ML Platform Code
│   ├── src/                     # Source code
│   ├── tests/                   # Unit & integration tests
│   ├── docker/                  # Container definitions
│   └── requirements.txt         # Python dependencies
├── 🔄 ci-cd/                     # CI/CD Configurations
│   └── providers/               # Multiple CI/CD providers
│       ├── jenkins/
│       └── ...
├── 📜 scripts/                   # Automation scripts
├── 📚 docs/                      # Documentation
└── 🧪 tests/                     # End-to-end tests
```

## 🛠️ Available Commands

### Infrastructure Management
```bash
make init ENV=dev              # Initialize Terraform
make plan ENV=dev              # Plan infrastructure changes
make apply ENV=dev             # Apply infrastructure changes
make destroy ENV=dev           # Destroy infrastructure
make test                      # Run infrastructure tests
```

### MLOps Stack Management
```bash
make mlops-install             # Install MLOps stack
make mlops-uninstall           # Uninstall MLOps stack
make mlops-status              # Check stack status
make mlops-core                # Install core tools (MLflow + Monitoring)
make mlops-full                # Install full stack
```

### CI/CD Setup
```bash
make setup-github              # Setup GitHub Actions
make setup-gitlab              # Setup GitLab CI
make setup-circleci            # Setup CircleCI
make setup-jenkins             # Setup Jenkins
```

### Development
```bash
make dev-setup                 # Setup development environment
make validate-all              # Validate all configurations
make test-unit                 # Run unit tests
make test-integration          # Run integration tests
```

### Monitoring & Debugging
```bash
make logs-mlflow               # View MLflow logs
make logs-seldon               # View Seldon logs
make port-forward-grafana      # Access Grafana UI
make backup-mlflow             # Backup MLflow data
```

## 🔧 Configuration

### Environment Variables
```bash
# Infrastructure
export ENV=dev                 # Target environment
export AWS_REGION=us-west-2    # AWS region

# MLOps Stack
export MLOPS_TOOLS=mlflow,kubeflow,seldon,monitoring
export CI_PROVIDER=github      # CI/CD provider
```

### Customization Examples

#### 1. Use Different CI/CD Provider
```bash
# Switch to GitLab CI
CI_PROVIDER=gitlab make mlops-install

# Switch to CircleCI
CI_PROVIDER=circleci make mlops-install
```

#### 2. Install Specific Tools Only
```bash
# Only MLflow and monitoring
MLOPS_TOOLS=mlflow,monitoring make mlops-install

# Only Kubeflow
MLOPS_TOOLS=kubeflow make mlops-install
```

#### 3. Multi-Environment Deployment
```bash
# Deploy to staging
make apply ENV=staging
make mlops-core ENV=staging

# Deploy to production
make apply ENV=prod
make mlops-full ENV=prod
```

## 🏢 Enterprise Features

### 🔒 **Security**
- **IRSA** for secure AWS access from Kubernetes
- **VPC endpoints** for private service communication
- **KMS encryption** for all data at rest and in transit
- **Network policies** for microsegmentation
- **Container vulnerability scanning**

### 📊 **Monitoring & Observability**
- **Infrastructure metrics** with Prometheus
- **ML model monitoring** with custom metrics
- **Distributed tracing** for ML pipelines
- **Alerting** for model drift and performance degradation
- **Cost monitoring** and optimization

### 🔄 **GitOps & Automation**
- **Infrastructure as Code** with Terraform
- **Declarative deployments** with Kubernetes
- **Automated testing** with Terratest
- **Multi-environment promotion** pipelines
- **Rollback capabilities**

### 📈 **Scalability**
- **Horizontal Pod Autoscaling** for ML workloads
- **Cluster Autoscaling** for cost optimization
- **Spot instance support** for training workloads
- **Multi-AZ deployment** for high availability

## 🧪 Testing

### Infrastructure Tests
```bash
# Run all infrastructure tests
make test

# Run specific module tests
cd infra/modules/vpc/test && go test -v
cd infra/modules/eks/test && go test -v
```

### ML Platform Tests
```bash
# Unit tests
make test-unit

# Integration tests
make test-integration

# End-to-end tests
cd tests/e2e && python -m pytest -v
```

## 📚 Documentation

- [MLOps Enterprise Recommendations](docs/mlops-enterprise-recommendations.md)
- [Infrastructure Architecture](docs/infrastructure-architecture.md)
- [Security Best Practices](docs/security-best-practices.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes
4. **Test** your changes: `make validate-all && make test`
5. **Commit** your changes: `git commit -m 'Add amazing feature'`
6. **Push** to the branch: `git push origin feature/amazing-feature`
7. **Submit** a pull request

## 🆘 Support

### Common Issues
```bash
# Check MLOps stack status
make mlops-status

# View logs
make logs-mlflow
make logs-seldon

# Validate configuration
make validate-all
```

### Getting Help
- 📖 Check the [documentation](docs/)
- 🐛 Report issues in GitHub Issues
- 💬 Join our community discussions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **HashiCorp** for Terraform
- **Kubernetes** community
- **MLflow** team
- **Kubeflow** community
- **Seldon** team
- **Prometheus** & **Grafana** teams

---

**Built with ❤️ for the MLOps community**