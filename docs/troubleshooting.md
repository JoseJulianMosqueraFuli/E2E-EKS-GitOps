# Troubleshooting

[← Documentation index](README.md)

Failures found while making the kind E2E test pass in GitHub Actions, with their cause and fix.
Each entry links the change that fixed it, so the same symptom can be traced quickly.

## Where to look first

- **E2E artifacts:** the `chaos-kind-evidence` artifact of each `E2E (kind)` run keeps pods, events,
  workflows, Litmus resources and container logs for 14 days.
- **Smoke test output:** on failure, `scripts/e2e/kind-smoke.sh` prints a pod summary
  (`scripts/e2e/pod_summary.py`) with restarts, waiting reasons and termination reasons.
- **Chaos workflows:** `scripts/e2e/kind-chaos.sh` prints the failed nodes, pod status and the last log
  lines of each workflow pod when a workflow ends in an unexpected phase or times out.

## MLflow

| Symptom | Cause | Fix |
|---|---|---|
| Training ends without `model-uri.txt` / `run-id.txt`; MLflow returns 404 for `/api/2.0/mlflow/logged-models` | MLflow client 3.x talking to a 2.x server | Keep the client (`ml-platform/poetry.lock`) and the server (`ml-platform/Dockerfile.mlflow-server`) on the same version, currently 3.17.1. A GitOps test checks the parity |
| MLflow pods are `OOMKilled`, restart, and fail with table creation conflicts on first start | Two workers per pod, and several replicas creating the schema at the same time | One worker, 1536 MiB in dev/staging/kind and 2 GiB in prod. The `initialize-mlflow-database` init container serializes schema creation with a PostgreSQL lock (`37f5508`). Existing databases need an explicit migration |
| `evaluate-model-step` fails downloading the model; signed URLs point to `dev-mlflow-minio:9000` | The short Service name does not resolve from the `argo-workflows` namespace | Use the full name `<prefix>-mlflow-minio.mlflow.svc.cluster.local:9000` (`1159cc1`, `0626076`) |
| The S3 gateway image cannot be pulled (401 from Docker Hub and quay.io) | MinIO stopped publishing community images | Replaced by Versity Gateway `versity/versitygw:v1.8.0` (`8a07e34`). Resources keep the `mlflow-minio` names (backlog #57) |
| PostgreSQL does not start on kind | The image runs as UID 70, not 999 | `runAsUser: 70` and `fsGroup: 70` in the StatefulSet (`e45f7dd`) |

## Argo Workflows

| Symptom | Cause | Fix |
|---|---|---|
| `argo-server` in `CrashLoopBackOff` with `Error: issuer empty` | `--auth-mode=sso` without an `sso` block in the ConfigMap | `--auth-mode=client` (Kubernetes token + RBAC) until an OIDC provider exists (backlog #47) |
| Submitted workflows stay untouched by the controller | `instanceID` requires the `workflows.argoproj.io/controller-instanceid` label on every Workflow | `instanceID` removed; there is a single controller (backlog #45) |
| The controller does not start when `persistence` is configured | Workflow archiving requires PostgreSQL or MySQL | Archiving disabled until a database is provided (backlog #46) |
| Steps fail to start on the emissary executor | Without `command`, emissary looks up the entrypoint in the image registry, which fails for images loaded into kind | Explicit `command: [python, -m, src.cli]` in each step (`2ca2b2e`) |

## Model serving

| Symptom | Cause | Fix |
|---|---|---|
| The `default-model` predictor restarts and ArgoCD reports `model-serving` as degraded on a new cluster | The predictor resolves `@champion` at startup, and no model has been registered yet | Run the training pipeline. Once `@champion` exists, the next restart or deployment loads it |
| `model-deployment-template` fails at `reject-candidate` | `verify` rejected the new version (it never reported the expected version, returned `4xx`, or its predictions differ from the registry). `restore-champion` and `verify-rollback` show whether the previous version is serving again | Read the `verify` logs. The rollout annotation `mlops-platform/model-version` on the InferenceService shows the version rolled out last |

## Chaos and Litmus

| Symptom | Cause | Fix |
|---|---|---|
| Service `litmus-chaos-exporter` is rejected | `prometheus.io/*` keys were under `metadata.labels`, where `/` is not allowed | Moved to `metadata.annotations`; a regression test checks labels (`47b8228`) |
| Workflow scripts fail: kubectl tries `http://localhost:8080` | The script containers had no kubeconfig | `KUBECONFIG=/chaos/kubeconfig`, built from the ServiceAccount CA and `tokenFile` (`cb0d779`) |
| `prepare-canary` in `ImagePullBackOff` with a malformed `mlops-platform:0.1.0` reference | Account/region replacements reached WorkflowTemplate image fields that the Kustomize image transformer did not know | `images-config.yaml` declares the WorkflowTemplate image paths (`b89faa0`) |
| Cleanup check fails after `Stop` | Engines end in `stopped`, not `completed`, when the workflow is cancelled | The engine wait accepts both states and reports the actual one (`fada72f`) |

## Python and CI

| Symptom | Cause | Fix |
|---|---|---|
| Feast tests fail inside the Docker `test` stage with `FileNotFoundError` | `.dockerignore` excluded `feature_store.yaml` and `feature_definitions.py` | Both files are copied into the `test` stage (`104e203`) |
| `poetry install` in `gitops/` tries to install a package that does not exist | Poetry treated the tooling directory as a package | `package-mode = false` in `gitops/pyproject.toml` |
