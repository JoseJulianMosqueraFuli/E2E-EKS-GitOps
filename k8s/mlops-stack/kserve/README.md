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
| `default-model` InferenceService | — | ArgoCD app `model-serving-<env>`, `gitops/applications/apps/model-serving/` | Namespace `models` |
| `model-predictor` ServiceAccount | — | `gitops/applications/apps/model-serving/base/` | No API token |
| NetworkPolicies | — | `kserve/base/` (controller webhook), `model-serving/base/` (predictors) | |

`Standard` mode creates a Deployment and a ClusterIP Service per InferenceService. It does not need
Knative or an Istio ingress gateway. KServe overlays add the environment prefix (`dev-`, `staging-`,
`prod-`); `kustomizeconfig.yaml` keeps the Flux `sourceRef` and `dependsOn` names aligned with that prefix.
The `model-serving` overlays only set the environment image and MLflow address, because each environment
runs on its own cluster.

## Declare a served model

What is served is declared in Git; which version is served is decided by the MLflow registry. The
InferenceService in `gitops/applications/apps/model-serving/base/inference-service.yaml` runs
`step serve --model-name default-model --alias champion` on the `mlops-platform` image. The predictor
reads the model from MLflow, which proxies the artifacts, so it needs no S3 credentials. The namespace
`models` enforces the `restricted` Pod Security Standard.

To serve another model, add an InferenceService with the registered model name as both its name and its
`--model-name`. The deployment template addresses the InferenceService by the model name.

The server resolves the alias once at startup and keeps that version until it restarts. Until the model
has a `@champion`, the predictor exits at startup and Kubernetes keeps restarting it. It uses the MLflow
scoring protocol:

| Request | Result |
|---|---|
| `GET /ping` | `200` when the model is loaded |
| `POST /invocations` with `{"dataframe_split": {"columns": [...], "data": [...]}}` | `{"predictions": [...]}` |
| Input that does not match the model signature | `400` |

Every response carries `X-Model-Name` and `X-Model-Version` headers.

## Deploy a new version

No image is built per model. `ml-pipeline-template` calls `model-deployment-template` after an approved
training run:

| Step | What it does |
|---|---|
| `register-model` (training) | Points `@champion` to the new version and outputs the version it replaced as `previous-version` |
| `roll-out` | Patches `spec.predictor.annotations["mlops-platform/model-version"]`; KServe rolls the predictor Deployment, and new pods load `@champion`. `maxUnavailable: 0` keeps the serving replica until a new one is ready |
| `verify` | Waits until responses carry `X-Model-Version: <new>`, then compares three predictions with `models:/<name>/<new>`. A `4xx` answer fails at once |
| `restore-champion` | Only on failure: moves `@champion` back to `previous-version`, or removes it when there was none |
| `roll-back`, `verify-rollback` | Only on failure and with a previous version: roll the predictor back and verify that version |
| `reject-candidate` | Only on failure: marks the workflow as failed after the rollback |

The annotation is not declared in Git, so an ArgoCD sync leaves it in place. It records the version the
predictor was last rolled out for. To run a deployment by hand:

```bash
argo -n argo-workflows submit --from workflowtemplate/model-deployment-template \
  -p model-version=2 -p previous-version=1 \
  -p mlflow-tracking-uri=http://dev-mlflow-server.mlflow:5000
```

To return to an earlier version without retraining, move the alias and roll it out. Pass the version
being replaced as `previous-version`; without it, a failed verification removes `@champion`.

```bash
python -m src.cli step set-alias --model-name default-model --version 1
argo -n argo-workflows submit --from workflowtemplate/model-deployment-template \
  -p model-version=1 -p previous-version=2 \
  -p mlflow-tracking-uri=http://dev-mlflow-server.mlflow:5000
```

## Verify a deployment

```bash
python -m src.cli step validate-deployment \
  --url http://default-model-predictor.models.svc.cluster.local/invocations \
  --data-uri s3://mlops-curated-data/training/data.csv \
  --model-uri models:/default-model/2 \
  --expected-version 2
```

The command sends three rows, waits until the endpoint reports the expected version and fails if the
served predictions differ from the registry model. GitHub Actions runs the deployment template on kind
(`make e2e-kind-serve`) after training, backup and Chaos tests. It deploys v1, promotes v2, and checks
that a v3 with a different input schema is rejected and v2 is restored.

## Network access

| Pods | Allowed ingress | Allowed egress |
|---|---|---|
| KServe controller (`kserve`) | Webhook port 9443 | Kubernetes API (443/6443), DNS |
| Predictors (`models`) | Port 8080 from `argo-workflows`, `monitoring` and the same namespace | MLflow (5000), DNS |

## Not included yet

- External exposure with TLS (Gateway API or Istio). Predictors are reachable only inside the cluster.
- Autoscaling and canary rollouts. KServe 0.21 supports canary traffic through Gateway API `HTTPRoute`s
  in `Standard` mode.
- Serialized deployments. Two pipelines that promote the same model at the same time can race on the alias.
- Serving metrics and alerts.
- Prebuilt serving runtimes (`kserve-runtime-configs` chart). The manifests in `examples/` reference those
  runtimes and do not run on this installation.

## Troubleshooting

```bash
kubectl -n flux-system get helmrelease cert-manager
kubectl -n kserve get helmreleases
kubectl -n kserve logs deployment/kserve-controller-manager -c manager --tail=100
kubectl -n models get inferenceservices
kubectl -n models get inferenceservice default-model -o jsonpath='{.spec.predictor.annotations}'
kubectl -n models logs -l serving.kserve.io/inferenceservice=default-model --tail=100
```
