set -eu
. "${CHAOS_SCRIPTS_DIR:-/chaos}/common.sh"
stop_engines

if [ "${CLEANUP_NODE_TAINTS:-false}" = true ]; then
  state=$(kubectl --request-timeout=10s get chaosengine -n litmus \
    -l "chaos.mlops-platform/workflow=$WORKFLOW_NAME" -o json)
  nodes=$(printf '%s' "$state" | jq -er '[.items[].spec.experiments[].spec.components.env[] | select(.name == "TARGET_NODE") | .value] | unique | .[]') || {
    [ "$(printf '%s' "$state" | jq '.items | length')" -eq 0 ] || exit 1
    nodes=''
  }
  for node in $nodes; do
    state=$(kubectl --request-timeout=10s get node "$node" -o json)
    patch=$(printf '%s' "$state" | jq -c --arg owner "$WORKFLOW_NAME" '
      [.spec.taints // [] | to_entries[] |
        select(.value.key == "chaos.litmuschaos.io/az-failure" and .value.value == $owner)] |
      reverse | map([
        {op: "test", path: ("/spec/taints/" + (.key | tostring)), value: .value},
        {op: "remove", path: ("/spec/taints/" + (.key | tostring))}
      ]) | add // []')
    [ "$patch" = '[]' ] || kubectl --request-timeout=10s patch node "$node" --type=json -p "$patch"
  done
fi

kubectl --request-timeout=10s delete configmap "$WORKFLOW_NAME-probe-ready" \
  -n argo-workflows --ignore-not-found
