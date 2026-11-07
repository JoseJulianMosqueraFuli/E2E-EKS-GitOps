# KServe Model Serving

[← Documentation index](../../../docs/README.md)

> The source of truth is `gitops/applications/apps/kserve/`. This directory is a legacy Kustomize
> entrypoint that only references its base; edit the manifests under `gitops/`.

KServe serves the model version that the MLflow registry alias `@champion` points to. Predictors run the
same `mlops-platform` image as the pipeline steps (`step serve`), so inference uses the exact dependencies
the model was trained with.

## What gets installed

| Component | Version | Installed by | Notes |
|---|---|---|---|
| cert-manager | v1.21.3 | Flux, `gitops/infrastructure/addons/cert-manager/` | Issues the KServe webhook certificate |
| KServe CRDs | v0.21.0 | Flux `HelmRelease` `kserve-crd` (chart `oci://ghcr.io/kserve/charts/kserve-crd`) | |
| KServe controller | v0.21.0 | Flux `HelmRelease` `kserve` (chart `kserve-resources`) | `Standard` deployment mode, ingress creation disabled |
| `model-predictor` ServiceAccount | — | `gitops/applications/apps/kserve/base/` | Namespace `models`, no API token |
| NetworkPolicies | — | `gitops/applications/apps/kserve/base/` | Controller webhook; predictor traffic |

`Standard` mode creates a Deployment and a ClusterIP Service per InferenceService. It does not need
Knative or an Istio ingress gateway. Overlays add the environment prefix (`dev-`, `staging-`, `prod-`);
`kustomizeconfig.yaml` keeps the Flux `sourceRef` and `dependsOn` names aligned with that prefix.

## Serve a registered model

The model must already be registered with the `@champion` alias (the training pipeline does this).
The predictor reads it from MLflow, which proxies the artifacts, so it needs no S3 credentials.

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: e2e-model
  namespace: models
spec:
  predictor:
    minReplicas: 1
    serviceAccountName: dev-model-predictor
    containers:
      - name: kserve-container
        image: <account>.dkr.ecr.<region>.amazonaws.com/mlops-dev-trainer:0.1.0
        args: [step, serve, --model-name, e2e-model, --port, "8080"]
        env:
          - name: MLFLOW_TRACKING_URI
            value: http://dev-mlflow-server.mlflow:5000
        ports:
          - containerPort: 8080
        readinessProbe:
          httpGet: {path: /ping, port: 8080}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities: {drop: [ALL]}
          seccompProfile: {type: RuntimeDefault}
        volumeMounts:
          - {name: tmp, mountPath: /tmp}
    volumes:
      - {name: tmp, emptyDir: {}}
```

The full manifest, with resources and liveness probe, is in [`scripts/e2e/kind-serve.sh`](../../../scripts/e2e/kind-serve.sh).
The namespace `models` enforces the `restricted` Pod Security Standard.

The server resolves the alias once at startup and keeps that version until it restarts. It uses the
MLflow scoring protocol:

| Request | Result |
|---|---|
| `GET /ping` | `200` when the model is loaded |
| `POST /invocations` with `{"dataframe_split": {"columns": [...], "data": [...]}}` | `{"predictions": [...]}` |
| Input that does not match the model signature | `400` |

Every response carries `X-Model-Name` and `X-Model-Version` headers.

## Verify a deployment

```bash
python -m src.cli step validate-deployment \
  --url http://e2e-model-predictor.models.svc.cluster.local/invocations \
  --data-uri s3://mlops-curated-data/training/data.csv \
  --model-uri models:/e2e-model@champion
```

The command sends three rows and fails if the served predictions differ from the registry model.
GitHub Actions runs the same check on kind (`make e2e-kind-serve`) after training, backup and Chaos tests.

## Network access

| Pods | Allowed ingress | Allowed egress |
|---|---|---|
| KServe controller (`kserve`) | Webhook port 9443 | Kubernetes API (443/6443), DNS |
| Predictors (`models`) | Port 8080 from `argo-workflows`, `monitoring` and the same namespace | MLflow (5000), DNS |

## Not included yet

- External exposure with TLS (Gateway API or Istio). Predictors are reachable only inside the cluster.
- Autoscaling and canary rollouts. KServe 0.21 supports canary traffic through Gateway API `HTTPRoute`s
  in `Standard` mode.
- Serving metrics and alerts.
- Prebuilt serving runtimes (`kserve-runtime-configs` chart). The manifests in `examples/` reference those
  runtimes and do not run on this installation.

## Troubleshooting

```bash
kubectl -n flux-system get helmrelease cert-manager
kubectl -n kserve get helmreleases
kubectl -n kserve logs deployment/kserve-controller-manager -c manager --tail=100
kubectl -n models get inferenceservices
kubectl -n models logs -l serving.kserve.io/inferenceservice=e2e-model --tail=100
```
