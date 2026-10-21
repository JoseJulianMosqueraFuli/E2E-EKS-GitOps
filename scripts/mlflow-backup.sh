#!/usr/bin/env bash
set -euo pipefail
ENVIRONMENT="${ENV:-dev}"
case "$ENVIRONMENT" in dev|staging|prod) ;; *) echo "ENV must be dev, staging or prod" >&2; exit 1 ;; esac
MODE="${1:-backup}"
case "$MODE" in
  backup) ;;
  restore)
    : "${BACKUP_KEY:?Set BACKUP_KEY to the S3 dump object key}"
    : "${RESTORE_DATABASE:?Set RESTORE_DATABASE to a separate empty database}"
    ;;
  *) echo "Usage: $0 [backup|restore]" >&2; exit 1 ;;
esac
export MODE
kc() {
  if [ -n "${KUBE_CONTEXT:-}" ]; then kubectl --context "$KUBE_CONTEXT" "$@"; else kubectl "$@"; fi
}
job="mlflow-${MODE}-$(date +%s)"
kc -n mlflow create job "$job" --from="cronjob/${ENVIRONMENT}-postgres-backup" --dry-run=client -o json |
  python3 -c '
import json, os, sys
job = json.load(sys.stdin)
job["spec"]["ttlSecondsAfterFinished"] = 86400
job["spec"]["backoffLimit"] = 0
if os.environ["MODE"] == "restore":
    job["spec"]["template"]["spec"]["containers"][0]["args"] = [
        "step", "restore-db", "--key", os.environ["BACKUP_KEY"], "--database", os.environ["RESTORE_DATABASE"]
    ]
print(json.dumps(job))
' | kc create -f -
trap 'kc -n mlflow logs "job/$job"' EXIT
kc -n mlflow wait --for=condition=Complete "job/$job" --timeout=2450s
