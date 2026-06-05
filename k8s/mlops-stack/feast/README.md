# Feast Feature Store - Kubernetes Deployment

This directory contains Kubernetes manifests for deploying Feast 
with Redis as the online store backend.

For local development, the SQLite/Parquet backend in `feature_repo/feature_store.yaml`
is sufficient. These manifests are for staging/production on EKS.

## Components

- `feast-server.yaml` - Feast server Deployment + Service
- `redis.yaml` - Redis StatefulSet for online store
- `kustomization.yaml` - Kustomize overlay

## Usage

```bash
# Deploy to the feast namespace
kubectl apply -k k8s/mlops-stack/feast/

# Or apply individual manifests
kubectl apply -f k8s/mlops-stack/feast/redis.yaml
kubectl apply -f k8s/mlops-stack/feast/feast-server.yaml
```

## Configuration

Update the `feature_store.yaml` ConfigMap in `feast-server.yaml` to point
at the Redis service instead of SQLite for production:

```yaml
online_store:
    type: redis
    connection_string: "redis://feast-redis-master:6379"
```

For AWS deployments, consider using ElastiCache Redis or DynamoDB instead.
