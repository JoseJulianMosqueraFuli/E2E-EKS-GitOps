# KServe Model Serving Platform

This directory contains Kubernetes manifests for deploying KServe, a cloud-native model serving platform that provides serverless inference, canary deployments, and multi-framework support for the MLOps platform.

## Overview

KServe provides:
q

- **Serverless Model Serving**: Automatic scaling to zero and scale-to-demand
- **Multi-Framework Support**: TensorFlow, PyTorch, Scikit-learn, XGBoost, and more
- **Canary Deployments**: Safe rollout of new model versions with traffic splitting
- **Model Explainability**: Built-in support for model explanations
- **Performance Optimization**: GPU support, batching, and caching

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   External      │    │   Istio         │    │   Knative       │
│   Traffic       │───▶│   Gateway       │───▶│   Serving       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KServe Controller                            │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │  InferenceService│              │  ServingRuntime │          │
│  │   Management    │              │   Management    │          │
│  └─────────────────┘              └─────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Model Serving Pods                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Predictor     │  │   Transformer   │  │   Explainer     │ │
│  │   (Model)       │  │ (Preprocessing) │  │ (Explanations)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │   S3 Model      │
                    │   Artifacts     │
                    └─────────────────┘
```

## Components

### Core Components

- **KServe Controller**: Manages InferenceService lifecycle and deployments
- **Admission Webhooks**: Validates and mutates InferenceService configurations
- **Serving Runtimes**: Framework-specific model servers (sklearn, pytorch, tensorflow)

### Supporting Components

- **Istio Integration**: Traffic management, load balancing, and security
- **Knative Serving**: Serverless scaling and request routing
- **Cert-Manager**: TLS certificate management for webhooks
- **Prometheus Monitoring**: Metrics collection and alerting

## Prerequisites

1. **EKS Cluster**: Running Kubernetes cluster with the following components:

   - Istio service mesh
   - Knative Serving
   - Cert-Manager
   - Prometheus (for monitoring)

2. **S3 Buckets**: Model artifacts storage with IRSA access

3. **IAM Roles**:
   - KServe controller role for managing resources
   - Model serving role for S3 access

## Installation

### 1. Install Prerequisites

#### Install Istio

```bash
# Install Istio
curl -L https://istio.io/downloadIstio | sh -
istioctl install --set values.defaultRevision=default

# Enable sidecar injection for models namespace
kubectl label namespace models istio-injection=enabled
```

#### Install Knative Serving

```bash
# Install Knative Serving
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.8.0/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.8.0/serving-core.yaml

# Install Knative Istio controller
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.8.0/net-istio.yaml
```

#### Install Cert-Manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

### 2. Deploy KServe

```bash
# Apply all manifests using kustomize
kubectl apply -k k8s/mlops-stack/kserve/

# Verify deployment
kubectl get pods -n kserve-system
kubectl get crd | grep kserve
kubectl get clusterservingruntimes
```

### 3. Configure Storage and RBAC

Update the following configurations before deployment:

#### S3 Bucket Configuration

Edit `storage-config.yaml`:

```yaml
stringData:
  s3: |
    {
      "bucket": "YOUR-MODEL-ARTIFACTS-BUCKET",
      "region": "YOUR-AWS-REGION"
    }
```

#### IAM Role ARNs

Update service account annotations:

```yaml
annotations:
  eks.amazonaws.com/role-arn: arn:aws:iam::YOUR-ACCOUNT:role/kserve-models-s3-role
```

### 4. Verify Installation

```bash
# Check KServe controller logs
kubectl logs -n kserve-system deployment/kserve-controller-manager -f

# Test with example InferenceService
kubectl apply -f k8s/mlops-stack/kserve/examples/sklearn-inference-service.yaml

# Check InferenceService status
kubectl get inferenceservices -n models
kubectl describe inferenceservice sklearn-iris-model -n models
```

## Usage

### Creating InferenceServices

#### Basic Sklearn Model

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: my-sklearn-model
  namespace: models
spec:
  predictor:
    model:
      modelFormat:
        name: sklearn
      storageUri: s3://my-bucket/models/sklearn-model/
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          cpu: 500m
          memory: 1Gi
```

#### PyTorch Model with Canary

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: my-pytorch-model
  namespace: models
spec:
  predictor:
    pytorch:
      storageUri: s3://my-bucket/models/pytorch-model-v1/
  canary:
    trafficPercent: 10
    pytorch:
      storageUri: s3://my-bucket/models/pytorch-model-v2/
```

#### Model with Transformer

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: my-model-with-transformer
  namespace: models
spec:
  predictor:
    model:
      modelFormat:
        name: sklearn
      storageUri: s3://my-bucket/models/model/
  transformer:
    containers:
      - name: transformer
        image: my-registry/feature-transformer:latest
        env:
          - name: PREDICTOR_HOST
            value: "my-model-with-transformer-predictor"
```

### Making Predictions

#### REST API

```bash
# Get inference service URL
kubectl get inferenceservice my-sklearn-model -n models

# Make prediction request
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"instances": [[5.1, 3.5, 1.4, 0.2]]}' \
  http://my-sklearn-model.models.example.com/v1/models/my-sklearn-model:predict
```

#### gRPC API

```python
import grpc
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2_grpc

# Create gRPC channel
channel = grpc.insecure_channel('my-tensorflow-model.models.example.com:80')
stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)

# Create prediction request
request = predict_pb2.PredictRequest()
request.model_spec.name = 'my-tensorflow-model'
request.model_spec.signature_name = 'serving_default'

# Make prediction
response = stub.Predict(request)
```

### Managing Model Versions

#### Canary Deployment

```bash
# Deploy canary version
kubectl patch inferenceservice my-model -n models --type='merge' -p='{
  "spec": {
    "canary": {
      "trafficPercent": 10,
      "model": {
        "modelFormat": {"name": "sklearn"},
        "storageUri": "s3://my-bucket/models/model-v2/"
      }
    }
  }
}'

# Promote canary to 50%
kubectl patch inferenceservice my-model -n models --type='merge' -p='{
  "spec": {
    "canary": {
      "trafficPercent": 50
    }
  }
}'

# Promote canary to production (100%)
kubectl patch inferenceservice my-model -n models --type='merge' -p='{
  "spec": {
    "predictor": {
      "model": {
        "modelFormat": {"name": "sklearn"},
        "storageUri": "s3://my-bucket/models/model-v2/"
      }
    },
    "canary": null
  }
}'
```

#### Rollback

```bash
# Rollback to previous version
kubectl patch inferenceservice my-model -n models --type='merge' -p='{
  "spec": {
    "predictor": {
      "model": {
        "storageUri": "s3://my-bucket/models/model-v1/"
      }
    },
    "canary": null
  }
}'
```

## Monitoring and Observability

### Metrics

KServe exposes Prometheus metrics for:

- Request latency and throughput
- Model loading time and success rate
- Resource utilization
- Canary deployment status

### Dashboards

Create Grafana dashboards for:

- Inference service performance
- Model serving resource usage
- Canary deployment metrics
- Error rates and SLA compliance

### Alerts

Configured alerts for:

- Inference service downtime
- High latency (>1s p95)
- High error rate (>5%)
- Model loading failures
- Stuck canary deployments

### Logging

Structured logs are available for:

- Model loading and initialization
- Prediction requests and responses
- Error conditions and debugging
- Performance metrics

## Security

### Network Security

- Network policies restrict traffic between namespaces
- Istio provides mTLS for service-to-service communication
- Ingress gateway controls external access

### Authentication and Authorization

- IRSA-based AWS authentication for S3 access
- Kubernetes RBAC for resource access
- Optional authentication for inference endpoints

### Model Security

- Model artifacts encrypted at rest in S3
- Container image scanning for vulnerabilities
- Pod security standards enforcement

## Troubleshooting

### Common Issues

#### InferenceService Not Ready

```bash
# Check InferenceService status
kubectl describe inferenceservice MY-MODEL -n models

# Check pod logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=MY-MODEL

# Common causes:
# - Model artifacts not accessible in S3
# - Insufficient resources
# - Invalid model format
# - Network connectivity issues
```

#### Model Loading Failures

```bash
# Check storage initializer logs
kubectl logs -n models -l component=storage-initializer

# Check predictor container logs
kubectl logs -n models -l component=predictor

# Common causes:
# - S3 permissions issues
# - Invalid model format or structure
# - Missing dependencies in serving runtime
```

#### Traffic Routing Issues

```bash
# Check Knative services
kubectl get ksvc -n models

# Check Istio virtual services
kubectl get virtualservice -n models

# Check ingress gateway status
kubectl get gateway -n models
```

### Debug Commands

```bash
# List all KServe resources
kubectl get inferenceservices,servingruntimes,trainedmodels -A

# Check controller logs
kubectl logs -n kserve-system deployment/kserve-controller-manager -f

# Check webhook logs
kubectl logs -n kserve-system -l control-plane=kserve-controller-manager -c manager

# Test model endpoint
kubectl port-forward -n models svc/MY-MODEL-predictor-default 8080:80
curl http://localhost:8080/v1/models/MY-MODEL
```

## Performance Optimization

### Resource Tuning

```yaml
# Optimize resource requests and limits
spec:
  predictor:
    model:
      resources:
        requests:
          cpu: 500m # Adjust based on model complexity
          memory: 1Gi # Adjust based on model size
        limits:
          cpu: 2000m # Allow bursting for peak loads
          memory: 4Gi # Prevent OOM kills
```

### Autoscaling Configuration

```yaml
# Configure Knative autoscaling
metadata:
  annotations:
    autoscaling.knative.dev/minScale: "1" # Keep warm instances
    autoscaling.knative.dev/maxScale: "10" # Limit max instances
    autoscaling.knative.dev/target: "10" # Target concurrency
    autoscaling.knative.dev/window: "60s" # Scaling window
```

### GPU Support

```yaml
# Enable GPU for model serving
spec:
  predictor:
    pytorch:
      resources:
        limits:
          nvidia.com/gpu: 1
      nodeSelector:
        accelerator: nvidia-tesla-k80
```

## Examples

The `examples/` directory contains ready-to-use InferenceService configurations:

| Example                              | Description                    | Use Case                      |
| ------------------------------------ | ------------------------------ | ----------------------------- |
| `sklearn-inference-service.yaml`     | Scikit-learn model with canary | Classification, regression    |
| `pytorch-inference-service.yaml`     | PyTorch model serving          | Deep learning, NLP            |
| `tensorflow-inference-service.yaml`  | TensorFlow with GPU support    | Image classification, CNNs    |
| `xgboost-inference-service.yaml`     | XGBoost with batching          | Tabular data, fraud detection |
| `huggingface-inference-service.yaml` | HuggingFace transformers       | NLP, text generation, LLMs    |
| `custom-inference-service.yaml`      | Custom container server        | Any custom model              |
| `multi-model-inference-service.yaml` | Multiple models on one service | Cost optimization             |

### Quick Deploy Example

```bash
# Deploy sklearn model
kubectl apply -f k8s/mlops-stack/kserve/examples/sklearn-inference-service.yaml

# Check status
kubectl get inferenceservice -n models

# Test prediction
curl -X POST http://sklearn-iris-model.models.example.com/v1/models/sklearn-iris-model:predict \
  -H "Content-Type: application/json" \
  -d '{"instances": [[5.1, 3.5, 1.4, 0.2]]}'
```

## Integration

### MLflow Integration

Models from MLflow registry can be automatically deployed:

```python
# Register model in MLflow
mlflow.register_model(model_uri, "my-model")

# Deploy using Argo Workflows
# Workflow will create InferenceService from MLflow model URI
```

### Argo Workflows Integration

Automated deployment workflows:

- Model registration triggers deployment workflow
- Container image building and pushing
- InferenceService creation and validation
- Canary deployment automation

### Monitoring Integration

- Prometheus metrics collection
- Grafana dashboard automation
- Alert manager integration
- Custom SLO monitoring
