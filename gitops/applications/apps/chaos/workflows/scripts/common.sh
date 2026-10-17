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
