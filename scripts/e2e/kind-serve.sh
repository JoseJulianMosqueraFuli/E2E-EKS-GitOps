#!/usr/bin/env bash
set -euo pipefail
[ "${GITHUB_ACTIONS:-}" = true ] || { echo "This test runs only in GitHub Actions" >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${ROOT}/gitops/platform/aws.env"
CONTEXT="${KUBE_CONTEXT:-kind-mlops-e2e}"
case "$CONTEXT" in kind-*) ;; *) echo "A disposable kind context is required" >&2; exit 1 ;; esac
ML_IMAGE="${ML_IMAGE:-${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mlops-dev-trainer:0.1.5}"
MODEL_NAME="default-model"
TRACKING_URI="http://dev-mlflow-server.mlflow:5000"
WORKFLOW_TIMEOUT="${WORKFLOW_TIMEOUT:-900}"
TRAINING_DATA="s3://mlops-curated-data/training/data.csv"
SCHEMA_CHANGE_DATA="s3://mlops-curated-data/schema-change/data.csv"
STAGE="setup"
kc() { kubectl --context "$CONTEXT" "$@"; }
log() { STAGE="$*"; echo "=== $*"; }
source "${ROOT}/scripts/e2e/workflow-helpers.sh"

artifacts="${ROOT}/test-results/serving"
mkdir -p "$artifacts"
diagnostics() {
  rc=$?
  [ "$rc" -eq 0 ] || echo "::error title=serving e2e failed at: ${STAGE}::see the serving-kind-evidence artifact"
  kc get pods -A -o wide > "$artifacts/pods.txt" || true
  kc get events -A --sort-by=.lastTimestamp > "$artifacts/events.txt" || true
  kc get helmreleases,helmrepositories -A -o yaml > "$artifacts/flux.yaml" || true
  kc -n models get inferenceservices,deployments,replicasets,services -o yaml > "$artifacts/models.yaml" || true
  kc -n argo-workflows get workflows -o yaml > "$artifacts/workflows.yaml" || true
  for ns in cert-manager kserve models; do
    for pod in $(kc -n "$ns" get pods -o name 2>/dev/null); do
      kc -n "$ns" logs "$pod" --all-containers --tail=200 > "$artifacts/${ns}-${pod#pod/}.log" 2>&1 || true
    done
  done
  kc -n argo-workflows logs -l workflows.argoproj.io/workflow --all-containers --prefix --tail=200 \
    > "$artifacts/workflow-pods.log" 2>&1 || true
  exit "$rc"
}
trap diagnostics EXIT

served_version() {
  kc -n models get inferenceservice "$MODEL_NAME" -o json | python3 -c '
import json, sys
annotations = json.load(sys.stdin)["spec"]["predictor"].get("annotations", {})
print(annotations.get("mlops-platform/model-version", ""))
'
}

submit_deployment() {
  local version="$1" previous="$2"
  kc create -o name -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: e2e-deploy-
  namespace: argo-workflows
spec:
  workflowTemplateRef:
    name: model-deployment-template
  arguments:
    parameters:
      - name: model-name
        value: ${MODEL_NAME}
      - name: model-version
        value: "${version}"
      - name: previous-version
        value: "${previous}"
      - name: mlflow-tracking-uri
        value: ${TRACKING_URI}
      - name: validation-data
        value: ${TRAINING_DATA}
      - name: verification-timeout
        value: "300"
EOF
}

log "KServe controller through Flux and cert-manager"
KUBE_CONTEXT="$CONTEXT" bash "$ROOT/gitops/scripts/install-gitops-controllers.sh" flux
kc apply -f "$ROOT/gitops/infrastructure/sources/helm-repository.yaml"
kc apply -k "$ROOT/gitops/infrastructure/addons/cert-manager"
kc -n flux-system wait --for=condition=Ready helmrelease/cert-manager --timeout=420s
kc apply -k "$ROOT/gitops/applications/apps/kserve/overlays/dev"
kc -n kserve wait --for=condition=Ready helmrelease/dev-kserve-crd helmrelease/dev-kserve --timeout=600s
kc -n kserve rollout status deployment/kserve-controller-manager --timeout=300s

log "InferenceService declared in Git serves ${MODEL_NAME}@champion"
kc apply -k "$ROOT/gitops/applications/apps/model-serving/overlays/dev"
kc -n models wait --for=condition=Ready "inferenceservice/${MODEL_NAME}" --timeout=420s

log "Deploy v1, the champion registered by the smoke test"
DEPLOY1="$(submit_deployment 1 "")"
wait_workflow "$DEPLOY1"
expect "$(served_version)" "1" "rolled-out version"

log "Train and deploy v2"
TRAIN2="$(submit_training -1.0 "$TRAINING_DATA")"
wait_workflow "$TRAIN2"
expect "$(workflow_output "$TRAIN2" model-version)" "2" "v2 registered"
expect "$(workflow_output "$TRAIN2" previous-version)" "1" "v2 replaces"
DEPLOY2="$(submit_deployment 2 1)"
wait_workflow "$DEPLOY2"
expect "$(served_version)" "2" "rolled-out version"

log "Publish a dataset whose features differ from the serving contract"
kc -n argo-workflows delete pod e2e-schema-change --ignore-not-found
kc apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: e2e-schema-change
  namespace: argo-workflows
spec:
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: seed
      image: ${ML_IMAGE}
      imagePullPolicy: IfNotPresent
      command: [python, -c]
      args:
        - |
          import io
          import boto3
          import pandas as pd
          s3 = boto3.client("s3")
          body = s3.get_object(Bucket="mlops-curated-data", Key="training/data.csv")["Body"].read()
          df = pd.read_csv(io.BytesIO(body))
          df.insert(0, "num_extra", df["num_0"] * 2)
          buffer = io.BytesIO()
          df.to_csv(buffer, index=False)
          s3.put_object(Bucket="mlops-curated-data", Key="schema-change/data.csv", Body=buffer.getvalue())
          print("seeded", df.shape)
      env:
        - name: AWS_DEFAULT_REGION
          value: ${AWS_REGION}
      envFrom:
        - configMapRef:
            name: ml-step-env
        - secretRef:
            name: ml-step-credentials
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: [ALL]
EOF
kc -n argo-workflows wait --for=jsonpath='{.status.phase}'=Succeeded pod/e2e-schema-change --timeout=300s

log "v3 needs a feature production requests do not send: the gate must restore v2"
TRAIN3="$(submit_training -1.0 "$SCHEMA_CHANGE_DATA")"
wait_workflow "$TRAIN3"
expect "$(workflow_output "$TRAIN3" model-version)" "3" "v3 registered"
expect "$(workflow_output "$TRAIN3" previous-version)" "2" "v3 replaces"
DEPLOY3="$(submit_deployment 3 2)"
if wait_workflow "$DEPLOY3"; then
  echo "FAIL: the v3 deployment should have been rejected"
  exit 1
fi
expect "$(node_field "$DEPLOY3" verify phase)" "Failed" "v3 verification"
expect "$(node_field "$DEPLOY3" restore-champion phase)" "Succeeded" "champion restored"
expect "$(node_field "$DEPLOY3" verify-rollback phase)" "Succeeded" "v2 verified again"
expect "$(node_field "$DEPLOY3" reject-candidate phase)" "Failed" "deployment reported as failed"
expect "$(served_version)" "2" "rolled-back version"

log "Model serving verified: deploy by alias, promotion and rollback"
