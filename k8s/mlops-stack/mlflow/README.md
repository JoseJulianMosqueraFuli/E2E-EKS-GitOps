# MLflow Server Deployment

This directory contains Kubernetes manifests for deploying MLflow server with S3 backend storage and PostgreSQL metadata store for the MLOps platform.

## Overview

MLflow provides:
- **Experiment Tracking**: Log parameters, metrics, and artifacts for ML experiments
- **Model Registry**: Centralized model store with versioning and stage transitions
- **Model Serving**: Deploy models for inference (integrated with KServe)
- **Artifact Storage**: S3-based storage for model artifacts and experiment data

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ML Training   │    │  Argo Workflows │    │  Model Serving  │
│    Workloads    │───▶│   (Orchestrator) │───▶│   (KServe)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MLflow Server                                │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │   Experiment    │              │     Model       │          │
│  │    Tracking     │              │    Registry     │          │
│  └─────────────────┘              └─────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
         │                                       │
         ▼                                       ▼
┌─────────────────┐                    ┌─────────────────┐
│   PostgreSQL    │                    │   S3 Buckets    │
│   (Metadata)    │                    │   (Artifacts)   │
└─────────────────┘                    └─────────────────┘
```

## Components

### Core Components
- **MLflow Server**: Web UI and REST API for experiment tracking and model registry
- **PostgreSQL**: Metadata store for experiments, runs, and model registry
- **S3 Integration**: Artifact storage with IRSA-based authentication

### Supporting Components
- **Horizontal Pod Autoscaler**: Automatic scaling based on CPU/memory usage
- **Pod Disruption Budget**: Ensures availability during cluster maintenance
- **Network Policy**: Restricts network access for security
- **Backup CronJob**: Automated PostgreSQL backups to S3
- **Monitoring**: Prometheus metrics and alerting rules

## Prerequisites

1. **EKS Cluster**: Running Kubernetes cluster with IRSA configured
2. **S3 Buckets**: 
   - Model artifacts bucket (e.g., `mlops-model-artifacts`)
   - Backup bucket (e.g., `mlops-backups`)
3. **IAM Roles**: 
   - MLflow S3 access role
   - Backup S3 access role
4. **Storage Class**: `gp3` storage class for PostgreSQL persistence

## Installation

### 1. Update Configuration

Before deploying, update the following configurations:

#### S3 Bucket Names
Edit `deployment.yaml`:
```yaml
env:
- name: MLFLOW_ARTIFACT_ROOT
  value: "s3://YOUR-MODEL-ARTIFACTS-BUCKET/mlflow-artifacts"
```

#### IAM Role ARNs
Update service account annotations:
```yaml
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::YOUR-ACCOUNT:role/mlops-mlflow-s3-role
```

#### Database Passwords
Update secrets with secure passwords:
```yaml
stringData:
  postgres-password: "YOUR-SECURE-PASSWORD"
```

### 2. Deploy MLflow

```bash
# Apply all manifests using kustomize
kubectl apply -k k8s/mlops-stack/mlflow/

# Verify deployment
kubectl get pods -n mlflow
kubectl get svc -n mlflow
kubectl get pvc -n mlflow
```

### 3. Verify Installation

```bash
# Check MLflow server logs
kubectl logs -n mlflow deployment/mlflow-server -f

# Check PostgreSQL logs
kubectl logs -n mlflow deployment/postgres -f

# Port forward to access UI (development)
kubectl port-forward -n mlflow svc/mlflow-server 5000:5000
```

Access MLflow UI at: http://localhost:5000

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MLFLOW_BACKEND_STORE_URI` | PostgreSQL connection string | Auto-generated |
| `MLFLOW_ARTIFACT_ROOT` | S3 artifact storage path | `s3://bucket/mlflow-artifacts` |
| `MLFLOW_SERVER_HOST` | Server bind address | `0.0.0.0` |
| `MLFLOW_SERVER_PORT` | Server port | `5000` |
| `MLFLOW_SERVER_WORKERS` | Gunicorn workers | `4` |
| `AWS_DEFAULT_REGION` | AWS region | `us-west-2` |

### Resource Configuration

#### MLflow Server
- **Requests**: 1Gi memory, 500m CPU
- **Limits**: 2Gi memory, 1000m CPU
- **Replicas**: 2 (with HPA scaling 2-10)

#### PostgreSQL
- **Requests**: 512Mi memory, 250m CPU
- **Limits**: 1Gi memory, 500m CPU
- **Storage**: 20Gi persistent volume

### Scaling Configuration

The HPA automatically scales MLflow server based on:
- CPU utilization > 70%
- Memory utilization > 80%
- Min replicas: 2
- Max replicas: 10

## Usage

### Experiment Tracking

```python
import mlflow
import mlflow.sklearn

# Set tracking URI
mlflow.set_tracking_uri("http://mlflow-server.mlflow:5000")

# Start experiment
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_param("batch_size", 32)
    
    # Log metrics
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_metric("loss", 0.05)
    
    # Log model
    mlflow.sklearn.log_model(model, "model")
```

### Model Registry

```python
import mlflow

# Register model
model_uri = "runs:/RUN_ID/model"
mlflow.register_model(model_uri, "my-model")

# Transition model stage
client = mlflow.MlflowClient()
client.transition_model_version_stage(
    name="my-model",
    version=1,
    stage="Production"
)
```

### CLI Usage

```bash
# List experiments
mlflow experiments list --tracking-uri http://mlflow-server.mlflow:5000

# Search runs
mlflow runs search --experiment-id 1 --tracking-uri http://mlflow-server.mlflow:5000

# Download artifacts
mlflow artifacts download --run-id RUN_ID --tracking-uri http://mlflow-server.mlflow:5000
```

## Security

### Network Security
- Network policies restrict ingress/egress traffic
- Only authorized namespaces can access MLflow
- PostgreSQL is not exposed outside the cluster

### Authentication
- IRSA-based AWS authentication for S3 access
- Kubernetes RBAC for service account permissions
- Optional basic auth for MLflow UI (configure in secrets)

### Data Encryption
- S3 artifacts encrypted at rest with KMS
- PostgreSQL data encrypted using EBS encryption
- TLS encryption for all network traffic

## Monitoring

### Metrics
MLflow server exposes Prometheus metrics:
- HTTP request metrics (latency, throughput, errors)
- Database connection metrics
- Application-specific metrics

### Alerts
Configured alerts for:
- MLflow server downtime
- High latency (>2s p95)
- High error rate (>10%)
- PostgreSQL connectivity issues
- High database connection usage

### Dashboards
Create Grafana dashboards for:
- MLflow server performance
- Database metrics
- Experiment tracking usage
- Model registry activity

## Backup and Recovery

### Automated Backups
- Daily PostgreSQL backups at 2 AM UTC
- Backups stored in S3 with 30-day retention
- Backup verification and cleanup

### Manual Backup
```bash
# Create manual backup
kubectl create job --from=cronjob/postgres-backup manual-backup-$(date +%Y%m%d) -n mlflow
```

### Recovery
```bash
# Restore from backup
kubectl exec -it postgres-POD -n mlflow -- psql -U mlflow -d mlflow < backup.sql
```

## Troubleshooting

### Common Issues

#### MLflow Server Won't Start
```bash
# Check logs
kubectl logs -n mlflow deployment/mlflow-server

# Common causes:
# - PostgreSQL not ready
# - S3 permissions issues
# - Invalid configuration
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
kubectl get pods -n mlflow -l app=postgres

# Test connection
kubectl exec -it postgres-POD -n mlflow -- psql -U mlflow -d mlflow -c "SELECT 1;"
```

#### S3 Access Issues
```bash
# Check IRSA configuration
kubectl describe sa mlflow-sa -n mlflow

# Verify IAM role permissions
aws sts assume-role --role-arn ROLE_ARN --role-session-name test
```

### Debug Commands

```bash
# Check all resources
kubectl get all -n mlflow

# Describe problematic pods
kubectl describe pod POD_NAME -n mlflow

# Check events
kubectl get events -n mlflow --sort-by='.lastTimestamp'

# Check network connectivity
kubectl exec -it mlflow-server-POD -n mlflow -- curl -v postgres:5432
```

## Maintenance

### Updating MLflow Version
1. Update image tag in `kustomization.yaml`
2. Test in development environment
3. Apply rolling update: `kubectl apply -k k8s/mlops-stack/mlflow/`

### Database Maintenance
```bash
# Connect to PostgreSQL
kubectl exec -it postgres-POD -n mlflow -- psql -U mlflow -d mlflow

# Check database size
SELECT pg_size_pretty(pg_database_size('mlflow'));

# Vacuum and analyze
VACUUM ANALYZE;
```

### Scaling Operations
```bash
# Manual scaling
kubectl scale deployment mlflow-server --replicas=5 -n mlflow

# Check HPA status
kubectl get hpa -n mlflow

# Update HPA limits
kubectl patch hpa mlflow-server-hpa -n mlflow -p '{"spec":{"maxReplicas":15}}'
```

## Integration

### Argo Workflows Integration
MLflow is automatically configured for use with Argo Workflows:
- Workflow templates reference MLflow tracking URI
- Artifacts are stored in S3 and registered in MLflow
- Model deployment workflows trigger based on model registry events

### KServe Integration
Models registered in MLflow can be deployed using KServe:
- Model URIs from MLflow registry
- Automatic container image building
- Canary deployments with model versioning

### Monitoring Integration
MLflow metrics are collected by Prometheus:
- ServiceMonitor for automatic discovery
- Custom alerts for MLflow-specific issues
- Integration with existing monitoring stack