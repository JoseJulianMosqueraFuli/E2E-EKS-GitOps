#!/usr/bin/env bash
set -euo pipefail
[ "${GITHUB_ACTIONS:-}" = true ] || { echo "This test runs only in GitHub Actions" >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTEXT="${KUBE_CONTEXT:-kind-mlops-e2e}"
case "$CONTEXT" in kind-*) ;; *) echo "A disposable kind context is required" >&2; exit 1 ;; esac
kc() { kubectl --context "$CONTEXT" "$@"; }
artifacts="${ROOT}/test-results/chaos"
mkdir -p "$artifacts"
diagnostics() {
  rc=$?
  kc get pods -A -o wide > "$artifacts/pods.txt" || true
  kc get events -A --sort-by=.lastTimestamp > "$artifacts/events.txt" || true
  kc -n argo-workflows get workflows -o yaml > "$artifacts/workflows.yaml" || true
  kc -n litmus get chaosengines,chaosresults,helmreleases -o yaml > "$artifacts/litmus.yaml" || true
  for ns in litmus flux-system argo-workflows mlflow; do
    for pod in $(kc -n "$ns" get pods -o name); do
      kc -n "$ns" logs "$pod" --all-containers --tail=200 > "$artifacts/${ns}-${pod#pod/}.log" 2>&1 || true
    done
  done
  exit "$rc"
}
trap diagnostics EXIT
KUBE_CONTEXT="$CONTEXT" bash "$ROOT/gitops/scripts/install-gitops-controllers.sh" flux
for ns in argocd kserve; do
  kc create namespace "$ns" --dry-run=client -o yaml | kc apply -f -
done
kc apply -k "$ROOT/gitops/applications/apps/chaos/overlays/dev"
kc -n litmus wait --for=condition=Ready helmrelease/litmus-core --timeout=420s
kc -n litmus wait --for=condition=Ready helmrelease/kubernetes-chaos --timeout=420s
kc -n litmus get chaosexperiment/pod-delete
[ "$(kc auth can-i delete pods -n mlflow --as=system:serviceaccount:litmus:litmus-pod-mlflow)" = yes ]
if kc auth can-i patch nodes --as=system:serviceaccount:litmus:litmus-pod-mlflow; then exit 1; fi
if kc auth can-i get secrets -A --as=system:serviceaccount:litmus:litmus-pod-mlflow; then exit 1; fi
if kc auth can-i patch nodes --as=system:serviceaccount:argo-workflows:chaos-workflow-mlflow; then exit 1; fi
submit() {
  kc create -o jsonpath='{.metadata.name}' -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: e2e-chaos-
  namespace: argo-workflows
spec:
  workflowTemplateRef:
    name: mlflow-resilience-test
  arguments:
    parameters:
    - name: chaos-duration
      value: "$1"
    - name: max-acceptable-downtime-seconds
      value: "15"
EOF
}
wait_workflow() {
  local name="$1" expected="$2" phase=""
  for ((attempt=0; attempt<90; attempt++)); do
    phase="$(kc -n argo-workflows get workflow "$name" -o jsonpath='{.status.phase}')"
    case "$phase" in
      Succeeded|Failed|Error) [ "$phase" = "$expected" ]; return ;;
    esac
    sleep 5
  done
  echo "Workflow $name timed out in phase $phase" >&2
  return 1
}
check_cleanup() {
  local name="$1"
  kc -n litmus get chaosengines -l "chaos.mlops-platform/workflow=$name" -o json | jq -e '.items | length > 0 and all(.[]; .status.engineStatus == "completed")'
  [ -z "$(kc -n argo-workflows get configmap "$name-probe-ready" --ignore-not-found -o name)" ]
  kc -n argo-workflows get workflow "$name" -o json | jq -e '[.status.nodes[] | select(.templateName == "stop-chaos")] | length == 1 and all(.[]; .phase == "Succeeded")'
  kc -n mlflow rollout status deployment/dev-mlflow-server --timeout=180s
}
workflow="$(submit 30)"
wait_workflow "$workflow" Succeeded
kc -n litmus get chaosresult "$workflow-pod-delete" -o json | jq -e '.status.experimentStatus.verdict == "Pass"'
check_cleanup "$workflow"
workflow="$(submit 180)"
active=false
for ((attempt=0; attempt<60; attempt++)); do
  if kc -n litmus get chaosengine "$workflow" --ignore-not-found -o json | jq -e '.status.engineStatus == "initialized"' >/dev/null; then
    active=true
    break
  fi
  sleep 3
done
[ "$active" = true ] || { echo "No active experiment observed for cancellation" >&2; exit 1; }
kc -n argo-workflows patch workflow "$workflow" --type merge -p '{"spec":{"shutdown":"Stop"}}'
wait_workflow "$workflow" Failed
check_cleanup "$workflow"
echo "Chaos injection, data continuity and cancellation cleanup passed"
