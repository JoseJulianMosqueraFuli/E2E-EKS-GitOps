# Feast Feature Store - Kubernetes Deployment

This directory is a legacy entrypoint that points to the GitOps source of truth in `gitops/applications/apps/feast/base/`.
The Feast + Redis manifests are maintained there.

For local development, the SQLite/Parquet backend in `feature_repo/feature_store.yaml`
is sufficient. These manifests are for staging/production on EKS.

## Components

- `kustomization.yaml` - Legacy entrypoint pointing to `gitops/applications/apps/feast/base/`

## Usage

```bash
# Deploy to the feast namespace from GitOps source of truth
kubectl apply -k gitops/applications/apps/feast/overlays/dev/
```

## Configuration

Update the `feature_store.yaml` ConfigMap in `gitops/applications/apps/feast/base/feast-server.yaml` to point
at the Redis service instead of SQLite for production:

```yaml
online_store:
    type: redis
    connection_string: "redis://feast-redis-master:6379"
```

For AWS deployments, consider using ElastiCache Redis or DynamoDB instead.
