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

| Template                    | Description                                     | Use Case              |
| --------------------------- | ----------------------------------------------- | --------------------- |
| `data-validation-template`  | Validates data quality using Great Expectations | Before training       |
| `model-training-template`   | End-to-end model training with MLflow           | Training pipeline     |
| `model-deployment-template` | Deploys models to KServe                        | Production deployment |
| `model-retraining-template` | Automatic retraining based on drift/performance | Model maintenance     |
| `ml-pipeline-template`      | Complete E2E pipeline orchestrating all stages  | Full automation       |

### Example Workflows

| Example                          | Description                              | Command                                                     |
| -------------------------------- | ---------------------------------------- | ----------------------------------------------------------- |
| `simple-training-workflow.yaml`  | Basic training workflow with sample data | `kubectl create -f examples/simple-training-workflow.yaml`  |
| `data-validation-workflow.yaml`  | Data quality validation pipeline         | `kubectl create -f examples/data-validation-workflow.yaml`  |
| `model-deployment-workflow.yaml` | Deploy model to KServe                   | `kubectl create -f examples/model-deployment-workflow.yaml` |
| `scheduled-ml-pipeline.yaml`     | Daily scheduled training (CronWorkflow)  | `kubectl apply -f examples/scheduled-ml-pipeline.yaml`      |

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

### 2. Access Argo UI

```bash
# Port forward to access UI
kubectl port-forward svc/argo-server -n argo-workflows 2746:2746

# Open browser at https://localhost:2746
```

### 3. Configure S3 Access

Update the IRSA role ARN in `artifact-repository-secret.yaml` for S3 artifact storage.

## Quick Start

### Run a Simple Training Workflow

```bash
# Create the workflow
kubectl create -f k8s/mlops-stack/argo-workflows/examples/simple-training-workflow.yaml

# Watch the workflow
argo watch -n argo-workflows @latest

# Get workflow logs
argo logs -n argo-workflows @latest
```

### Run Data Validation

```bash
# Validate data quality
kubectl create -f k8s/mlops-stack/argo-workflows/examples/data-validation-workflow.yaml

# Check results
argo get -n argo-workflows @latest
```

### Deploy a Model

```bash
# Deploy model to KServe
kubectl create -f k8s/mlops-stack/argo-workflows/examples/model-deployment-workflow.yaml
```

### Schedule Daily Training

```bash
# Create scheduled pipeline (runs daily at 2 AM UTC)
kubectl apply -f k8s/mlops-stack/argo-workflows/examples/scheduled-ml-pipeline.yaml

# Check cron workflows
kubectl get cronworkflows -n argo-workflows
```

## Using Workflow Templates

### Submit Workflow from Template

```bash
# Using data-validation-template
argo submit -n argo-workflows --from workflowtemplate/data-validation-template \
  -p data-source="s3://my-bucket/data/" \
  -p validation-suite="production"

# Using model-training-template
argo submit -n argo-workflows --from workflowtemplate/model-training-template \
  -p data-path="s3://my-bucket/curated-data/" \
  -p model-name="my-classifier" \
  -p experiment-name="experiment-v1"

# Using model-retraining-template
argo submit -n argo-workflows --from workflowtemplate/model-retraining-template \
  -p model-name="production-model" \
  -p performance-threshold="0.85" \
  -p auto-deploy="true"
```

## Workflow Parameters

### Data Validation Template

| Parameter          | Default                    | Description                        |
| ------------------ | -------------------------- | ---------------------------------- |
| `data-source`      | `s3://mlops-raw-data/`     | Input data location                |
| `validation-suite` | `default`                  | Great Expectations suite name      |
| `output-path`      | `s3://mlops-curated-data/` | Output location for validated data |

### Model Training Template

| Parameter             | Default                            | Description            |
| --------------------- | ---------------------------------- | ---------------------- |
| `data-path`           | `s3://mlops-curated-data/`         | Training data location |
| `model-name`          | `default-model`                    | Model name for MLflow  |
| `experiment-name`     | `default-experiment`               | MLflow experiment name |
| `mlflow-tracking-uri` | `http://mlflow-server.mlflow:5000` | MLflow server URL      |

### Model Retraining Template

| Parameter               | Default            | Description                   |
| ----------------------- | ------------------ | ----------------------------- |
| `model-name`            | `production-model` | Model to evaluate/retrain     |
| `performance-threshold` | `0.85`             | Minimum accuracy threshold    |
| `drift-threshold`       | `0.1`              | Data drift threshold          |
| `auto-deploy`           | `false`            | Auto-deploy if model improves |

## Monitoring

### View Workflow Status

```bash
# List all workflows
argo list -n argo-workflows

# Get workflow details
argo get -n argo-workflows <workflow-name>

# View logs
argo logs -n argo-workflows <workflow-name>
```

### Prometheus Metrics

Argo Workflows exposes metrics at `/metrics` endpoint:

- `argo_workflows_count` - Total workflow count by status
- `argo_workflows_pods_count` - Pod count by phase
- `argo_workflow_operation_duration_seconds` - Operation latency

## Troubleshooting

### Common Issues

1. **Workflow stuck in Pending**

   ```bash
   kubectl describe workflow <name> -n argo-workflows
   kubectl get events -n argo-workflows
   ```

2. **S3 artifact errors**

   - Verify IRSA role has S3 permissions
   - Check artifact-repository-secret configuration

3. **Pod failures**
   ```bash
   argo logs -n argo-workflows <workflow-name> --follow
   kubectl logs <pod-name> -n argo-workflows
   ```

## Best Practices

1. **Use WorkflowTemplates** for reusable pipeline components
2. **Set resource limits** on all containers
3. **Configure TTL** for automatic workflow cleanup
4. **Use artifacts** for passing data between steps
5. **Implement retries** for transient failures
6. **Monitor with Prometheus/Grafana** dashboards

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
          port: 443 # HTTPS
        - protocol: TCP
          port: 5000 # MLflow
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
