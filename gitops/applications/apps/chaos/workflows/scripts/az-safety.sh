set -eu
state_dir="${CHAOS_STATE_DIR:-/tmp}"
kubectl --request-timeout=10s get pods --all-namespaces -o json > "$state_dir/cluster-pods.json"
jq -e --slurpfile targets "$state_dir/nodes.json" '
  all(.items[] | select(.status.phase != "Succeeded" and .status.phase != "Failed") |
    select(.spec.nodeName as $node | any($targets[0][]; .node == $node));
    all(.spec.volumes[]?; .persistentVolumeClaim == null))
' "$state_dir/cluster-pods.json" >/dev/null || {
  echo "ERROR: target zone contains PVC-backed workloads; validate cross-zone storage recovery first" >&2
  exit 1
}
jq -e --arg zone "$ZONE" --slurpfile nodes "$state_dir/cluster-nodes.json" '
  def cpu: tostring | if endswith("m") then rtrimstr("m") | tonumber / 1000 else tonumber end;
  def memory:
    tostring | capture("^(?<n>[0-9.]+)(?<u>Ki|Mi|Gi|Ti|K|M|G|T)?$") |
    (.n | tonumber) * ({Ki:1024,Mi:1048576,Gi:1073741824,Ti:1099511627776,K:1000,M:1000000,G:1000000000,T:1000000000000}[.u // ""] // 1);
  def requests:
    [.spec.containers[]?, .spec.initContainers[]? | .resources.requests // {}] + [(.spec.overhead // {})] |
    {cpu: ([.[] | (.cpu // "0" | cpu)] | add // 0), memory: ([.[] | (.memory // "0" | memory)] | add // 0), gpu: ([.[] | (."nvidia.com/gpu" // "0" | tonumber)] | add // 0)};
  [$nodes[0].items[] | select(.metadata.labels["topology.kubernetes.io/zone"] == $zone) | .metadata.name] as $targets |
  [$nodes[0].items[] | select(.metadata.labels["topology.kubernetes.io/zone"] != null and .metadata.labels["topology.kubernetes.io/zone"] != $zone) |
    select(.spec.unschedulable != true) | select(any(.status.conditions[]?; .type == "Ready" and .status == "True")) |
    select(all(.spec.taints[]?; .effect != "NoSchedule" and .effect != "NoExecute"))] as $survivors |
  [$survivors[].metadata.name] as $names |
  [.items[] | select(.status.phase != "Succeeded" and .status.phase != "Failed")] as $pods |
  [$pods[] | select(.spec.nodeName as $node | $targets | index($node)) | requests] as $moving |
  [$pods[] | select(.spec.nodeName as $node | $names | index($node)) | requests] as $used |
  all($survivors[]; .status.allocatable.cpu != null and .status.allocatable.memory != null) and
  (([$survivors[].status.allocatable.cpu | cpu] | add // 0) - ([$used[].cpu] | add // 0) >= ([$moving[].cpu] | add // 0)) and
  (([$survivors[].status.allocatable.memory | memory] | add // 0) - ([$used[].memory] | add // 0) >= ([$moving[].memory] | add // 0)) and
  (([$survivors[].status.allocatable."nvidia.com/gpu" // "0" | tonumber] | add // 0) - ([$used[].gpu] | add // 0) >= ([$moving[].gpu] | add // 0))
' "$state_dir/cluster-pods.json" >/dev/null || {
  echo "ERROR: insufficient surviving CPU, memory or GPU capacity, or invalid resource quantities" >&2
  exit 1
}
