#!/usr/bin/env bash
set -euo pipefail
[ "${GITHUB_ACTIONS:-}" = true ] || { echo "This test runs only in GitHub Actions" >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${ROOT}/gitops/platform/aws.env"
CONTEXT="${KUBE_CONTEXT:-kind-mlops-e2e}"
case "$CONTEXT" in kind-*) ;; *) echo "A disposable kind context is required" >&2; exit 1 ;; esac
ML_IMAGE="${ML_IMAGE:-${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mlops-dev-trainer:0.1.0}"
MODEL_NAME="${MODEL_NAME:-e2e-model}"
TRACKING_URI="http://dev-mlflow-server.mlflow:5000"
kc() { kubectl --context "$CONTEXT" "$@"; }
artifacts="${ROOT}/test-results/serving"
mkdir -p "$artifacts"
diagnostics() {
  rc=$?
  kc get pods -A -o wide > "$artifacts/pods.txt" || true
  kc get events -A --sort-by=.lastTimestamp > "$artifacts/events.txt" || true
  kc get helmreleases,helmrepositories -A -o yaml > "$artifacts/flux.yaml" || true
  kc -n models get inferenceservices,deployments,services -o yaml > "$artifacts/models.yaml" || true
  for ns in cert-manager kserve models; do
    for pod in $(kc -n "$ns" get pods -o name 2>/dev/null); do
      kc -n "$ns" logs "$pod" --all-containers --tail=200 > "$artifacts/${ns}-${pod#pod/}.log" 2>&1 || true
    done
  done
  kc -n argo-workflows logs e2e-serving-check > "$artifacts/serving-check.log" 2>&1 || true
  exit "$rc"
}
trap diagnostics EXIT

KUBE_CONTEXT="$CONTEXT" bash "$ROOT/gitops/scripts/install-gitops-controllers.sh" flux
kc apply -f "$ROOT/gitops/infrastructure/sources/helm-repository.yaml"
kc apply -k "$ROOT/gitops/infrastructure/addons/cert-manager"
kc -n flux-system wait --for=condition=Ready helmrelease/cert-manager --timeout=420s
kc apply -k "$ROOT/gitops/applications/apps/kserve/overlays/dev"
kc -n kserve wait --for=condition=Ready helmrelease/dev-kserve-crd helmrelease/dev-kserve --timeout=600s
kc -n kserve rollout status deployment/kserve-controller-manager --timeout=300s

kc apply -f - <<EOF
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: ${MODEL_NAME}
  namespace: models
spec:
  predictor:
    minReplicas: 1
    serviceAccountName: dev-model-predictor
    containers:
      - name: kserve-container
        image: ${ML_IMAGE}
        imagePullPolicy: IfNotPresent
        args: [step, serve, --model-name, "${MODEL_NAME}", --port, "8080"]
        env:
          - name: MLFLOW_TRACKING_URI
            value: ${TRACKING_URI}
        ports:
          - containerPort: 8080
            protocol: TCP
        readinessProbe:
          httpGet:
            path: /ping
            port: 8080
        livenessProbe:
          httpGet:
            path: /ping
            port: 8080
          initialDelaySeconds: 30
        resources:
          requests:
            cpu: 100m
            memory: 512Mi
          limits:
            cpu: "1"
            memory: 1Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop: [ALL]
          seccompProfile:
            type: RuntimeDefault
        volumeMounts:
          - name: tmp
            mountPath: /tmp
    volumes:
      - name: tmp
        emptyDir: {}
EOF
kc -n models wait --for=condition=Ready "inferenceservice/${MODEL_NAME}" --timeout=420s
url="$(kc -n models get inferenceservice "${MODEL_NAME}" -o jsonpath='{.status.address.url}')"
url="${url:-http://${MODEL_NAME}-predictor.models.svc.cluster.local}"
echo "Inference endpoint: ${url}"

kc -n argo-workflows delete pod e2e-serving-check --ignore-not-found
kc apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: e2e-serving-check
  namespace: argo-workflows
spec:
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: check
      image: ${ML_IMAGE}
      imagePullPolicy: IfNotPresent
      args:
        - step
        - validate-deployment
        - --url
        - ${url}/invocations
        - --data-uri
        - s3://mlops-curated-data/training/data.csv
        - --model-uri
        - models:/${MODEL_NAME}@champion
      env:
        - name: AWS_DEFAULT_REGION
          value: ${AWS_REGION}
        - name: MLFLOW_TRACKING_URI
          value: ${TRACKING_URI}
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
phase=""
for ((attempt=0; attempt<60; attempt++)); do
  phase="$(kc -n argo-workflows get pod e2e-serving-check -o jsonpath='{.status.phase}')"
  case "$phase" in Succeeded|Failed) break ;; esac
  sleep 5
done
kc -n argo-workflows logs e2e-serving-check
[ "$phase" = Succeeded ] || { echo "Serving check ended in phase ${phase:-unknown}" >&2; exit 1; }
echo "Model serving verified: ${MODEL_NAME}@champion matches the registry predictions"
