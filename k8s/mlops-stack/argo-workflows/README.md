# Argo Workflows for MLOps Pipeline

This directory contains Kubernetes manifests for deploying Argo Workflows as the workflow orchestration engine for the MLOps platform.

## Overview

Argo Workflows provides:
- **Workflow Orchestration**: DAG-based ML pipeline execution
- **Artifact Management**: S3-based artifact storage and passing
- **Template Reusability**: Modular workflow templates for different ML stages
- **Event-driven Execution**: Trigger workflows based on data arrival or model updates
- **Monitoring Integration**: Metrics and logging for workflow observability

## Components

### Core Components
- **Workflow Controller**: Manages workflow execution and lifecycle
- **Argo Server**: Provides UI and API for workflow management
- **Custom Resource Definitions**: Workflow, WorkflowTemplate, CronWorkflow CRDs

### Workflow Templates
- **Data Validation Template**: Great Expectations-based data quality validation
- **Model Training Template**: MLflow-integrated model training pipeline
- **Model Deployment Template**: KServe-based model deployment automation
- **ML Pipeline Template**: End-to-end pipeline orchestrating all stages

## Prerequisites

1. **EKS Cluster**: Running Kubernetes cluster with IRSA configured
2. **S3 Buckets**: Artifact storage buckets (raw-data, curated-data, models)
3. **ECR Repository**: Container image registry for ML workloads
4. **MLflow Server**: Model registry and experiment tracking (deployed separately)

## Installation

### 1. Deploy Argo Workflows

```bash
# Apply all manifests using kustomize
kubectl apply -k k8s/mlops-stack/argo-workflows/

# Verify deployment
kubectl get pods -n argo-workflows
kubectl get svc -n argo-workflows
```

### 2. Configure S3 Access

Update the IRSA role ARN in `artifact-repository-secret.yaml`:

```yaml
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::YOUR_ACCOUNT:role/argo-workflows-s3-role
```

### 3. Update Configuration

Modify `configmap.yaml` to match your environment:
- S3 bucket names
- AWS region
- MLflow server URL
- ECR repository URL

## Usage

### Running Workflows

#### 1. Submit a Workflow from Template

```bash
# Submit data validation workflow
argo submit -n argo-workflows --from workflowtemplate/data-validation-template \
  --parameter data-source=s3://your-raw-data/ \
  --parameter validation-suite=production

# Submit complete ML pipeline
argo submit -n argo-workflows --from workflowtemplate/ml-pipeline-template \
  --parameter model-name=my-model \
  --parameter experiment-name=experiment-001
```

#### 2. Schedule Workflows with CronWorkflow

```bash
# Deploy scheduled pipeline
kubectl apply -f k8s/mlops-stack/argo-workflows/examples/scheduled-ml-pipeline.yaml

# List cron workflows
argo cron list -n argo-workflows
```

#### 3. Monitor Workflows

```bash
# List workflows
argo list -n argo-workflows

# Get workflow details
argo get WORKFLOW_NAME -n argo-workflows

# Watch workflow logs
argo logs WORKFLOW_NAME -n argo-workflows -f
```

### Accessing Argo UI

#### Port Forward (Development)

```bash
kubectl port-forward svc/argo-server -n argo-workflows 2746:2746
```

Access UI at: http://localhost:2746

#### Production Access

Configure ingress or load balancer for production access:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argo-server-ingress
  namespace: argo-workflows
spec:
  rules:
  - host: argo-workflows.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argo-server
            port:
              number: 2746
```

## Workflow Templates

### Data Validation Template

Validates data quality using Great Expectations:

```yaml
# Example parameters
parameters:
  data-source: "s3://mlops-raw-data/batch-001/"
  validation-suite: "production"
  output-path: "s3://mlops-curated-data/batch-001/"
```

### Model Training Template

Trains ML models with MLflow integration:

```yaml
# Example parameters
parameters:
  data-path: "s3://mlops-curated-data/batch-001/"
  model-name: "fraud-detection"
  experiment-name: "fraud-detection-v2"
  mlflow-tracking-uri: "http://mlflow-server.mlflow:5000"
```

### Model Deployment Template

Deploys models using KServe:

```yaml
# Example parameters
parameters:
  model-name: "fraud-detection"
  model-version: "3"
  deployment-namespace: "models"
  ecr-repository: "123456789012.dkr.ecr.us-west-2.amazonaws.com/mlops"
```

## Security Configuration

### RBAC Permissions

The workflow service accounts have minimal required permissions:
- Pod creation and management
- ConfigMap and Secret access
- Workflow resource management
- S3 access via IRSA

### Network Policies

Implement network policies to restrict pod-to-pod communication:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argo-workflows-netpol
  namespace: argo-workflows
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argo-workflows
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS
    - protocol: TCP
      port: 5000  # MLflow
```

## Monitoring and Observability

### Metrics Collection

Workflow controller exposes Prometheus metrics on port 9090:
- Workflow execution metrics
- Resource utilization
- Error rates and latency

### Logging

Structured logs are available through:
- Workflow controller logs
- Individual step logs
- Argo server API logs

### Alerting

Configure alerts for:
- Workflow failures
- Long-running workflows
- Resource exhaustion
- Artifact storage issues

## Troubleshooting

### Common Issues

1. **Pod Pending**: Check resource requests and node capacity
2. **S3 Access Denied**: Verify IRSA configuration and IAM policies
3. **Workflow Stuck**: Check workflow controller logs and resource limits
4. **Template Not Found**: Ensure WorkflowTemplate is in correct namespace

### Debug Commands

```bash
# Check workflow controller logs
kubectl logs -n argo-workflows deployment/workflow-controller

# Check argo server logs
kubectl logs -n argo-workflows deployment/argo-server

# Describe workflow for events
kubectl describe workflow WORKFLOW_NAME -n argo-workflows

# Check workflow step logs
argo logs WORKFLOW_NAME -n argo-workflows --step STEP_NAME
```

## Customization

### Adding New Workflow Templates

1. Create new template in `workflow-templates/` directory
2. Update `kustomization.yaml` to include new template
3. Apply changes: `kubectl apply -k k8s/mlops-stack/argo-workflows/`

### Environment-Specific Configuration

Use Kustomize overlays for different environments:

```bash
# Create environment overlay
mkdir -p k8s/overlays/production
# Add environment-specific patches
# Apply with overlay
kubectl apply -k k8s/overlays/production/
```