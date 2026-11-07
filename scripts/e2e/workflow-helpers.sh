#!/usr/bin/env bash

submit_training() {
  local min_improvement="$1" data_path="$2"
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
        value: ${data_path}
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

workflow_output() {
  kc -n argo-workflows get "$1" -o jsonpath="{.status.outputs.parameters[?(@.name==\"$2\")].value}"
}
