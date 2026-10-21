#!/usr/bin/env bash
set -euo pipefail
[ "${GITHUB_ACTIONS:-}" = true ] || { echo "This test runs only in GitHub Actions" >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTEXT="${KUBE_CONTEXT:-kind-mlops-e2e}"
case "$CONTEXT" in kind-*) ;; *) echo "A disposable kind context is required" >&2; exit 1 ;; esac
kc() { kubectl --context "$CONTEXT" "$@"; }
kc -n mlflow create configmap e2e-backup-check --from-file="$ROOT/scripts/e2e/backup_restore.py" --dry-run=client -o yaml | kc apply -f -
kc -n mlflow get cronjob dev-postgres-backup -o json | python3 -c '
import json, sys
cron = json.load(sys.stdin)
spec = cron["spec"]["jobTemplate"]["spec"]
container = spec["template"]["spec"]["containers"][0]
container["command"] = ["python", "/checks/backup_restore.py"]
container["args"] = []
container["env"].extend([
    {"name": "AWS_ENDPOINT_URL", "value": "http://dev-mlflow-minio:9000"},
    {"name": "AWS_ACCESS_KEY_ID", "valueFrom": {"secretKeyRef": {"name": "mlflow-minio-secrets", "key": "aws-access-key-id"}}},
    {"name": "AWS_SECRET_ACCESS_KEY", "valueFrom": {"secretKeyRef": {"name": "mlflow-minio-secrets", "key": "aws-secret-access-key"}}},
])
container["volumeMounts"].append({"name": "check", "mountPath": "/checks", "readOnly": True})
spec["template"]["spec"]["volumes"].append({"name": "check", "configMap": {"name": "e2e-backup-check"}})
spec["backoffLimit"] = 0
spec["activeDeadlineSeconds"] = 300
print(json.dumps({"apiVersion":"batch/v1", "kind":"Job", "metadata":{"name":"e2e-backup-restore", "namespace":"mlflow"}, "spec":spec}))
' | kc apply -f -
trap 'kc -n mlflow logs job/e2e-backup-restore --all-containers; kc -n mlflow get job/e2e-backup-restore -o yaml' EXIT
kc -n mlflow wait --for=condition=Complete job/e2e-backup-restore --timeout=330s
