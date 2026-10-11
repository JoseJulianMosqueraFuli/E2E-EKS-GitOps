#!/usr/bin/env bash
set -euo pipefail

image="${N8N_IMAGE:?Run this script through make test-n8n to supply the pinned image}"
workflow_timeout="${N8N_WORKFLOW_TIMEOUT:-5m}"
artifact_dir="${N8N_ARTIFACT_DIR:-n8n-test-artifacts}"
failure_dir="$artifact_dir/failures"
report="$artifact_dir/n8n-test-report.md"

mkdir -p "$failure_dir"
printf '# n8n workflow test report\n\nImage: `%s`\n\n| Workflow | Result |\n| --- | --- |\n' "$image" > "$report"

shopt -s nullglob
workflows=(n8n/workflows/*.json)
if [ "${#workflows[@]}" -eq 0 ]; then
  printf '| — | FAIL (no workflow JSON files found) |\n' >> "$report"
  cat "$report"
  exit 1
fi

passed=0
failed=0
for workflow in "${workflows[@]}"; do
  workflow_id=$(jq -er '.id | select(type == "string" and length > 0)' "$workflow" 2>/dev/null || true)
  if [[ ! "$workflow_id" =~ ^[A-Za-z0-9_-]+$ ]]; then
    printf '| `%s` | FAIL (missing or invalid workflow ID) |\n' "$(basename "$workflow")" >> "$report"
    failed=$((failed + 1))
    continue
  fi

  index=$((passed + failed + 1))
  log_file="$failure_dir/workflow-$index.log"
  container_name="n8n-ci-$$-$index"
  if timeout --signal=TERM --kill-after=30s "$workflow_timeout" docker run \
    --name "$container_name" \
    --network none \
    --read-only \
    --tmpfs /home/node/.n8n:rw,noexec,nosuid,size=64m,uid=1000,gid=1000 \
    --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --memory 1g \
    --cpus 1 \
    --pids-limit 256 \
    --env N8N_DIAGNOSTICS_ENABLED=false \
    --env N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
    --env EXECUTIONS_TIMEOUT=240 \
    --volume "$(realpath "$workflow"):/home/node/workflow.json:ro" \
    --entrypoint /bin/sh \
    "$image" \
    -c 'n8n import:workflow --input=/home/node/workflow.json && n8n execute --id="$1"' \
    n8n-test "$workflow_id" \
    >"$log_file" 2>&1; then
    docker rm -f "$container_name" >/dev/null 2>&1 || true
    rm -f "$log_file"
    printf '| `%s` | PASS |\n' "$(basename "$workflow")" >> "$report"
    passed=$((passed + 1))
  else
    docker rm -f "$container_name" >/dev/null 2>&1 || true
    printf '| `%s` | FAIL (import, execution, or %s timeout) |\n' "$(basename "$workflow")" "$workflow_timeout" >> "$report"
    tail -n 40 "$log_file"
    failed=$((failed + 1))
  fi
done

printf '\n**Result:** %s passed, %s failed.\n' "$passed" "$failed" >> "$report"
cat "$report"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  cat "$report" >> "$GITHUB_STEP_SUMMARY"
fi
[ "$failed" -eq 0 ]
