set -eu
. "${CHAOS_SCRIPTS_DIR:-/chaos}/common.sh"
validate_parameters
require_uint expected-engines "$EXPECTED_ENGINES" 1 20

trap 'status=$?; if [ "$status" -ne 0 ]; then stop_engines || echo "ERROR: automatic stop failed; inspect ChaosEngines" >&2; fi; exit "$status"' 0

code=$(probe_service)
[ "$code" = 200 ] || { echo "ERROR: baseline probe returned $code" >&2; exit 1; }
kubectl --request-timeout=10s create configmap "$WORKFLOW_NAME-probe-ready" \
  -n argo-workflows --from-literal=ready=true

deadline=$(( $(date +%s) + CHAOS_DURATION + 240 ))
max_downtime=0
outage_start=0
observed_active=false
output_file=${DOWNTIME_FILE:-/tmp/max_downtime.txt}
while [ "$(date +%s)" -lt "$deadline" ]; do
  request_start=$(date +%s)
  code=$(probe_service)
  now=$(date +%s)
  if [ "$code" != 200 ] && [ "$outage_start" -eq 0 ]; then
    outage_start=$request_start
  fi
  if [ "$outage_start" -ne 0 ]; then
    downtime=$(( now - outage_start ))
    [ "$downtime" -le "$max_downtime" ] || max_downtime=$downtime
    [ "$code" != 200 ] || outage_start=0
  fi
  echo "$max_downtime" > "$output_file"
  if [ "$max_downtime" -gt "$MAX_DOWNTIME_SECONDS" ]; then
    echo "ERROR: observed downtime ${max_downtime}s exceeds ${MAX_DOWNTIME_SECONDS}s" >&2
    exit 1
  fi
  state=$(kubectl --request-timeout=10s get chaosengine -n litmus \
    -l "chaos.mlops-platform/workflow=$WORKFLOW_NAME" -o json)
  count=$(printf '%s' "$state" | jq -er '.items | length')
  completed=$(printf '%s' "$state" | jq -er '[.items[] | select(.status.engineStatus == "completed")] | length')
  [ "$count" -le "$EXPECTED_ENGINES" ] || { echo "ERROR: unexpected engines" >&2; exit 1; }
  if [ "$count" -gt "$completed" ]; then
    observed_active=true
  fi
  if [ "$count" -eq "$EXPECTED_ENGINES" ] && [ "$completed" -eq "$count" ]; then
    [ "$observed_active" = true ] || { echo "ERROR: fault completed before observation" >&2; exit 1; }
    [ "$code" = 200 ] || { echo "ERROR: service did not recover" >&2; exit 1; }
    echo "Observed all $count engines through completion; maximum downtime ${max_downtime}s"
    exit 0
  fi
  sleep 1
done
echo "ERROR: engines did not complete within the monitoring deadline" >&2
exit 1
