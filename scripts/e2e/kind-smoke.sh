#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KIND_DIR="${ROOT}/scripts/e2e/kind"
CONTEXT="${KUBE_CONTEXT:-kind-mlops-e2e}"
ML_IMAGE="${ML_IMAGE:-mlops-platform:0.1.0}"
WORKFLOW_TIMEOUT="${WORKFLOW_TIMEOUT:-900}"
MODEL_NAME="e2e-model"

kc() { kubectl --context "${CONTEXT}" "$@"; }
log() { echo "=== $*"; }

diagnostics() {
  log "Diagnostics"
  kc get pods -A -o wide || true
  kc get pvc -A || true
  kc get events -A --sort-by=.lastTimestamp | tail -n 60 || true
  for ns in mlflow argo-workflows; do
    for pod in $(kc -n "${ns}" get pods -o name 2>/dev/null); do
      echo "--- ${ns}/${pod}"
      kc -n "${ns}" describe "${pod}" | tail -n 25 || true
      kc -n "${ns}" logs "${pod}" --all-containers --tail=80 || true
    done
  done
  kc -n argo-workflows get workflows -o yaml || true
}
trap 'rc=$?; [ "${rc}" -eq 0 ] || diagnostics; exit "${rc}"' EXIT

PG_PASSWORD="$(openssl rand -hex 16)"
S3_ACCESS_KEY="$(openssl rand -hex 10)"
S3_SECRET_KEY="$(openssl rand -hex 20)"

log "StorageClass gp3 backed by kind local-path"
kc apply -f - <<'EOF'
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
EOF

log "Argo Workflows"
kc apply --server-side -k "${KIND_DIR}/argo-workflows" >/dev/null 2>&1 || true
kc wait --for=condition=Established crd --all --timeout=120s
kc apply --server-side -k "${KIND_DIR}/argo-workflows"
kc -n argo-workflows rollout status deployment/workflow-controller --timeout=180s
kc -n argo-workflows rollout status deployment/argo-server --timeout=180s

log "MLflow (PostgreSQL + MinIO + tracking server)"
kc create namespace mlflow --dry-run=client -o yaml | kc apply -f -
kc -n mlflow create secret generic dev-mlflow-secrets \
  --from-literal=postgres-user=mlflow \
  --from-literal=postgres-password="${PG_PASSWORD}" \
  --from-literal=postgres-db=mlflow \
  --from-literal=backend_store_uri="postgresql://mlflow:${PG_PASSWORD}@dev-mlflow-postgresql:5432/mlflow" \
  --dry-run=client -o yaml | kc apply -f -
kc -n mlflow create secret generic dev-mlflow-minio-secrets \
  --from-literal=root-user="${S3_ACCESS_KEY}" \
  --from-literal=root-password="${S3_SECRET_KEY}" \
  --from-literal=aws-access-key-id="${S3_ACCESS_KEY}" \
  --from-literal=aws-secret-access-key="${S3_SECRET_KEY}" \
  --dry-run=client -o yaml | kc apply -f -
kc apply -k "${KIND_DIR}/mlflow"
kc -n mlflow rollout status statefulset/dev-mlflow-postgresql --timeout=300s
kc -n mlflow rollout status deployment/dev-mlflow-minio --timeout=300s
kc -n mlflow rollout status deployment/dev-mlflow-server --timeout=420s

log "Step configuration for kind (MinIO endpoint + credentials)"
kc -n argo-workflows create configmap ml-step-env \
  --from-literal=AWS_ENDPOINT_URL=http://dev-mlflow-minio.mlflow:9000 \
  --from-literal=MLFLOW_S3_ENDPOINT_URL=http://dev-mlflow-minio.mlflow:9000 \
  --dry-run=client -o yaml | kc apply -f -
kc -n argo-workflows create secret generic ml-step-credentials \
  --from-literal=AWS_ACCESS_KEY_ID="${S3_ACCESS_KEY}" \
  --from-literal=AWS_SECRET_ACCESS_KEY="${S3_SECRET_KEY}" \
  --dry-run=client -o yaml | kc apply -f -

log "Seed buckets and training data"
kc -n argo-workflows delete pod e2e-seed --ignore-not-found
kc apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: e2e-seed
  namespace: argo-workflows
spec:
  restartPolicy: Never
  containers:
    - name: seed
      image: ${ML_IMAGE}
      imagePullPolicy: IfNotPresent
      command: [python, -c]
      args:
        - |
          import io
          import boto3
          import numpy as np
          import pandas as pd
          from sklearn.datasets import make_classification
          s3 = boto3.client("s3")
          for bucket in ("mlflow-artifacts-dev", "mlops-curated-data", "mlops-artifacts-bucket"):
              try:
                  s3.create_bucket(Bucket=bucket)
              except s3.exceptions.BucketAlreadyOwnedByYou:
                  pass
          X, y = make_classification(n_samples=600, n_features=6, n_informative=4, random_state=7)
          df = pd.DataFrame(X, columns=[f"num_{i}" for i in range(X.shape[1])])
          df["segment"] = np.where(X[:, 0] > 0, "high", "low")
          df["target"] = y
          buffer = io.BytesIO()
          df.to_csv(buffer, index=False)
          s3.put_object(Bucket="mlops-curated-data", Key="training/data.csv", Body=buffer.getvalue())
          print("seeded", df.shape)
      env:
        - name: AWS_DEFAULT_REGION
          value: us-east-1
      envFrom:
        - configMapRef:
            name: ml-step-env
        - secretRef:
            name: ml-step-credentials
EOF
kc -n argo-workflows wait --for=jsonpath='{.status.phase}'=Succeeded pod/e2e-seed --timeout=300s
kc -n argo-workflows logs e2e-seed

submit_training() {
  local min_improvement="$1"
  kc create -o name -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: e2e-train-
  namespace: argo-workflows
spec:
  workflowTemplateRef:
    name: model-training-template
  arguments:
    parameters:
      - name: data-path
        value: s3://mlops-curated-data/training/data.csv
      - name: mlflow-tracking-uri
        value: http://dev-mlflow-server.mlflow:5000
      - name: model-name
        value: ${MODEL_NAME}
      - name: experiment-name
        value: e2e
      - name: hyperparameters
        value: '{"n_estimators": 50}'
      - name: min-improvement
        value: "${min_improvement}"
EOF
}

wait_workflow() {
  local name="$1" phase="" waited=0
  while [ "${waited}" -lt "${WORKFLOW_TIMEOUT}" ]; do
    phase="$(kc -n argo-workflows get "${name}" -o jsonpath='{.status.phase}')"
    case "${phase}" in
      Succeeded) log "${name} Succeeded"; return 0 ;;
      Failed|Error) log "${name} ${phase}"; return 1 ;;
    esac
    sleep 10
    waited=$((waited + 10))
  done
  log "${name} timed out (phase=${phase})"
  return 1
}

node_field() {
  local name="$1" node="$2" field="$3"
  kc -n argo-workflows get "${name}" -o json | python3 -c '
import json, sys
node, field = sys.argv[1], sys.argv[2]
nodes = json.load(sys.stdin)["status"]["nodes"].values()
match = [n for n in nodes if n.get("displayName") == node]
if not match:
    sys.exit(f"node {node} not found")
n = match[0]
if field == "phase":
    print(n.get("phase", ""))
else:
    params = {p["name"]: p.get("value", "") for p in n.get("outputs", {}).get("parameters", [])}
    print(params.get(field, ""))
' "${node}" "${field}"
}

expect() {
  local actual="$1" expected="$2" what="$3"
  if [ "${actual}" != "${expected}" ]; then
    echo "FAIL: ${what}: expected '${expected}', got '${actual}'"
    exit 1
  fi
  echo "OK: ${what} = ${actual}"
}

log "Run 1: first model must be approved and registered as champion"
WF1="$(submit_training 0.0)"
wait_workflow "${WF1}"
expect "$(node_field "${WF1}" evaluate-model model-approved)" "true" "run 1 model-approved"
expect "$(node_field "${WF1}" register-model phase)" "Succeeded" "run 1 register-model"
expect "$(node_field "${WF1}" register-model model-version)" "1" "run 1 model-version"

log "Run 2: candidate must beat the champion by 0.5 and be blocked"
WF2="$(submit_training 0.5)"
wait_workflow "${WF2}"
expect "$(node_field "${WF2}" evaluate-model model-approved)" "false" "run 2 model-approved"
expect "$(node_field "${WF2}" register-model phase)" "Skipped" "run 2 register-model"

log "End-to-end smoke test passed"
