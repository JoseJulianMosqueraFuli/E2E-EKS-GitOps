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
cleanup_container() {
  local name="$1"
  local retries=5
  docker stop --time 10 "$name" >/dev/null 2>&1 || true
  while (( retries > 0 )); do
    if docker rm -f "$name" >/dev/null 2>&1; then
      return 0
    fi
    if ! docker inspect "$name" >/dev/null 2>&1; then
      return 0
    fi
    retries=$((retries - 1))
    sleep 1
  done
  return 1
}

active_container=""
cleanup_on_exit() {
  if [ -n "$active_container" ]; then
    cleanup_container "$active_container" || true
  fi
}
trap cleanup_on_exit EXIT

for workflow in "${workflows[@]}"; do
  workflow_id=$(jq -er '.id | select(type == "string" and length > 0)' "$workflow" 2>/dev/null || true)
  if [[ ! "$workflow_id" =~ ^[A-Za-z0-9_-]+$ ]]; then
    printf '| `%s` | FAIL (missing or invalid workflow ID) |\n' "$(basename "$workflow")" | tee -a "$report"
    failed=$((failed + 1))
    continue
  fi

  index=$((passed + failed + 1))
  workflow_slug=$(basename "$workflow" .json | tr -cs '[:alnum:]._-' '-')
  workflow_slug="${workflow_slug:0:80}"
  workflow_slug="${workflow_slug%-}"
  log_file="$failure_dir/workflow-$index-$workflow_slug.log"
  container_name="n8n-ci-$$-$index"
  if ! docker create \
    --interactive \
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
    --entrypoint /bin/sh \
    "$image" \
    -c 'cat > /tmp/workflow.json && n8n import:workflow --input=/tmp/workflow.json && n8n execute --id="$1"' \
    n8n-test "$workflow_id" \
    >"$log_file" 2>&1; then
    printf '| `%s` | FAIL (container creation or image pull) |\n' "$(basename "$workflow")" >> "$report"
    tail -n 40 "$log_file"
    failed=$((failed + 1))
    continue
  fi

  active_container="$container_name"
  if timeout --signal=TERM --kill-after=30s "$workflow_timeout" docker start --attach --interactive "$container_name" <"$workflow" >>"$log_file" 2>&1; then
    start_status=0
  else
    start_status=$?
  fi

  if [[ "$start_status" == "124" || "$start_status" == "137" ]]; then
    oom_killed=$(docker inspect --format '{{.State.OOMKilled}}' "$container_name" 2>>"$log_file" || printf unknown)
    docker kill "$container_name" >/dev/null 2>&1 || true
    if cleanup_container "$active_container"; then
      active_container=""
    else
      printf 'Failed to remove container %s after interrupted execution.\n' "$active_container" >> "$log_file"
    fi
    if [[ "$oom_killed" == "true" ]]; then
      printf '| `%s` | FAIL (container exceeded its memory limit) |\n' "$(basename "$workflow")" >> "$report"
    else
      printf '| `%s` | FAIL (execution exceeded %s timeout) |\n' "$(basename "$workflow")" "$workflow_timeout" >> "$report"
    fi
    tail -n 40 "$log_file"
    failed=$((failed + 1))
    continue
  fi

  exit_code=$(docker inspect --format '{{.State.ExitCode}}' "$container_name" 2>>"$log_file" || printf unknown)
  if [[ "$start_status" != "0" || "$exit_code" != "0" ]]; then
    oom_killed=$(docker inspect --format '{{.State.OOMKilled}}' "$container_name" 2>>"$log_file" || printf unknown)
    failure_status="$exit_code"
    if [[ "$failure_status" == "0" || "$failure_status" == "unknown" ]]; then
      failure_status="$start_status"
    fi
    if cleanup_container "$active_container"; then
      active_container=""
    else
      printf 'Failed to remove container %s after execution failure.\n' "$active_container" >> "$log_file"
    fi
    if [[ "$oom_killed" == "true" ]]; then
      printf '| `%s` | FAIL (container exceeded its memory limit) |\n' "$(basename "$workflow")" >> "$report"
    else
      printf '| `%s` | FAIL (workflow exited with status %s) |\n' "$(basename "$workflow")" "$failure_status" >> "$report"
    fi
    tail -n 40 "$log_file"
    failed=$((failed + 1))
  elif cleanup_container "$active_container"; then
    active_container=""
    rm -f "$log_file"
    printf '| `%s` | PASS |\n' "$(basename "$workflow")" >> "$report"
    passed=$((passed + 1))
  else
    printf 'Failed to remove container %s after execution.\n' "$active_container" >> "$log_file"
    printf '| `%s` | FAIL (container cleanup failed) |\n' "$(basename "$workflow")" >> "$report"
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
