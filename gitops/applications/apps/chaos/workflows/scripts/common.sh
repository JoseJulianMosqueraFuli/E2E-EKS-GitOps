require_uint() {
  case "$2" in
    ''|*[!0-9]*|0[0-9]*) echo "ERROR: $1 must be a decimal integer without leading zeroes" >&2; return 1 ;;
  esac
  [ "${#2}" -le 4 ] && [ "$2" -ge "$3" ] && [ "$2" -le "$4" ] || {
    echo "ERROR: $1 must be between $3 and $4" >&2
    return 1
  }
}

validate_parameters() {
  require_uint chaos-duration "$CHAOS_DURATION" 1 300
  require_uint max-acceptable-downtime-seconds "$MAX_DOWNTIME_SECONDS" 0 60
  case "$PROBE_URL" in
    http://?*|https://?*) ;;
    *) echo "ERROR: a non-empty HTTP(S) probe URL is required" >&2; return 1 ;;
  esac
  if [ -n "${PROBE_BODY:-}" ]; then
    printf '%s' "$PROBE_BODY" | jq -e . >/dev/null
    [ -n "${PROBE_RESPONSE_FILTER:-}" ] || { echo "ERROR: a response assertion is required for prediction probes" >&2; return 1; }
  fi
}

probe_service() {
  if [ -n "${CANARY_RUN_ID:-}" ]; then
    api="${PROBE_URL%/health}/api/2.0/mlflow"
    payload=$(jq -nc --arg run "$CANARY_RUN_ID" --argjson timestamp "$(($(date +%s) * 1000))" '{run_id:$run,key:"chaos_probe",value:1,timestamp:$timestamp}')
    curl -sf --max-time 2 -H 'Content-Type: application/json' -d "$payload" "$api/runs/log-metric" >/dev/null || { echo 000; return; }
    response=$(curl -sf --max-time 2 "$api/runs/get?run_id=$CANARY_RUN_ID") || { echo 000; return; }
    printf '%s' "$response" | jq -e --arg workflow "$WORKFLOW_NAME" 'any(.run.data.params[]?; .key == "canary" and .value == $workflow)' >/dev/null || { echo 000; return; }
    echo 200
  elif [ -n "${PROBE_BODY:-}" ]; then
    response=$(curl -sf --max-time 2 -H 'Content-Type: application/json' -d "$PROBE_BODY" "$PROBE_URL") || { echo 000; return; }
    printf '%s' "$response" | jq -e "$PROBE_RESPONSE_FILTER" >/dev/null || { echo 000; return; }
    echo 200
  else
    curl -s -o /dev/null -w '%{http_code}' --max-time 2 "$PROBE_URL" || echo 000
  fi
}

wait_for_probe() {
  deadline=$(( $(date +%s) + 90 ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    marker=$(kubectl --request-timeout=10s get configmap "$WORKFLOW_NAME-probe-ready" \
      -n argo-workflows --ignore-not-found -o name) || return 1
    [ -z "$marker" ] || return 0
    sleep 1
  done
  echo "ERROR: availability probe did not start; no fault injected" >&2
  return 1
}

stop_engines() {
  engines=$(kubectl --request-timeout=10s get chaosengine -n litmus \
    -l "chaos.mlops-platform/workflow=$WORKFLOW_NAME" -o name) || return 1
  failed=0
  for engine in $engines; do
    kubectl --request-timeout=10s patch "$engine" -n litmus --type merge \
      -p '{"spec":{"engineState":"stop"}}' || failed=1
  done
  for engine in $engines; do
    kubectl --request-timeout=130s wait "$engine" -n litmus \
      --for=jsonpath='{.status.engineStatus}'=completed --timeout=120s || failed=1
  done
  return "$failed"
}
