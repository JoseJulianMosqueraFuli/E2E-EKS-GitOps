# Chaos Engineering Stack — Internal Runbook

**Application**: `chaos`  
**Namespace**: `litmus` (experiments) + `argo-workflows` (validation workflows)  
**Tool**: LitmusChaos (`litmus-core` operator + `kubernetes-chaos` experiment catalog)  
**Deployed via**: ArgoCD ApplicationSet `mlops-applications`  
**High-level proposal**: see [`docs/chaos-engineering-proposal.md`](../../../../docs/chaos-engineering-proposal.md)

---

## Review status (2026-10-20)

The implementation has local regression coverage and a GitHub Actions kind scenario. A green run of the
new scenario and execution in EKS remain required; neither is implied by a successful local render.

- Bootstrap uses the complete pinned Flux distribution, including CRDs and controller RBAC. The ArgoCD
  installer waits for the actual application-controller StatefulSet.
- MLflow canaries write a parameter and artifact before injection, verify run continuity while the fault
  is active, and read the same artifact afterwards. MLflow proxies artifacts through the tracking server.
- Zone tests require a JSON prediction request and a jq response assertion. Preflight rejects PVC-backed
  workloads in the target zone and insufficient surviving CPU/memory/GPU capacity. It also checks node
  readiness, taints and placement of Litmus/Argo control pods. Aggregate capacity does not prove affinity
  compatibility or storage HA; the current PostgreSQL/gateway design is not zone resilient.
- Pod, stress and node faults use separate accounts. Flux admission policies prevent the MLflow workflow
  from selecting a node account and constrain runner account selection. Their effective enforcement is
  included in the kind scenario and must also be verified in EKS.
- Kind CI covers a PostgreSQL backup/restore, real Litmus pod deletion and cancellation using Argo `Stop`,
  with evidence retained for 14 days. The default MLflow downtime budget is 5 seconds; the CI scenario
  explicitly uses 15 seconds. These budgets are test parameters, not a measured production SLO.

Both workflows use a shared mutex and a probe readiness barrier. Missing data, malformed prediction
responses, API errors, exceeded downtime and unfinished engines fail the workflow. Exit handlers stop
engines and verify completion. `argo terminate` or a failed workflow controller can bypass cleanup; manual
recovery remains necessary in those cases. `annotationCheck: "false"` is explicit because these manual
workflows select their targets and do not depend on an absent workload opt-in annotation.

Network partition remains disabled (#59); EC2 stop/termination is not enabled (#58). See the
[current backlog](../../../../docs/project/backlog.md#revision-operativa--2026-10-20) and the
[bootstrap/recovery contract](../../../../docs/architecture/platform-runtime-config.md).

Regression checks: [`test_chaos_safety.py`](../../../tests/test_chaos_safety.py) and
[`kind-chaos.sh`](../../../../scripts/e2e/kind-chaos.sh).

## What this directory contains

```
gitops/applications/apps/chaos/
├── base/
│   ├── kustomization.yaml      # Base Kustomize manifest
│   ├── namespace.yaml          # litmus namespace (privileged PSS)
│   ├── litmus.yaml             # HelmRepository + HelmReleases (litmus-core, kubernetes-chaos)
│   ├── rbac.yaml               # Separate pod, stress and node fault accounts
│   ├── exporter.yaml           # chaos-exporter Deployment + read-only RBAC
│   └── metrics-service.yaml    # litmus-chaos-exporter Service scraped by Prometheus
├── workflows/                  # Deployed in dev and staging only
│   ├── kustomization.yaml
│   ├── rbac.yaml               # Separate MLflow and node workflow accounts
│   ├── scripts/                # Shared readiness barrier, monitoring and cleanup scripts
│   ├── mlflow-resilience-test.yaml  # Phase 1: pod-delete MLflow + data/artifact checks
│   └── az-failure-test.yaml         # Phase 2: taint every node in one AZ
├── overlays/
│   ├── dev/                    # base + workflows, MLflow names with dev- prefix
│   ├── staging/                # base + workflows, MLflow names with staging- prefix
│   └── production/             # base only: no validation workflows
└── experiments/                # ChaosEngines applied by hand (not synced by ArgoCD)
    ├── README.md
    ├── pod-delete-mlflow.yaml
    ├── pod-delete-kserve-controller.yaml
    ├── pod-delete-argocd-controller.yaml
    ├── cpu-hog-mlflow.yaml
    ├── node-drain-worker.yaml
    ├── node-drain-gpu.yaml
    └── pod-network-partition-kserve-mlflow.yaml
```

---

## How it is deployed

The chaos stack is managed by the same ArgoCD `ApplicationSet` that deploys the rest of the MLOps platform.

Entry in `gitops/applications/projects/mlops-applicationset.yaml`:

```yaml
- app: chaos
  namespace: litmus
  component: chaos-engineering
```

When ArgoCD syncs, it creates an application `chaos-dev`, `chaos-staging`, or `chaos-production` depending on the environment.

---

## What gets installed

### 1. Namespace (`litmus`)

Marked with `pod-security.kubernetes.io/enforce: privileged` because Litmus helper pods need elevated privileges for some faults (e.g. `pod-cpu-hog` uses the containerd socket on the node).

### 2. HelmReleases (Flux)

Both charts come from `https://litmuschaos.github.io/litmus-helm/` and are pinned:

| Release | Chart | Version | Installs |
|---------|-------|---------|----------|
| `litmus-core` | `litmus-core` | `3.31.1` | CRDs (`ChaosEngine`, `ChaosExperiment`, `ChaosResult`) + chaos-operator (cluster-wide, `operatorMode: standard`) |
| `kubernetes-chaos` | `kubernetes-chaos` | `3.31.0` | `ChaosExperiment` definitions in `litmus` (`pod-delete`, `pod-cpu-hog`, `node-drain`, `node-taint`, `pod-network-partition`, …) |

There is no ChaosCenter portal and no MongoDB: experiments are submitted with `kubectl` or Argo Workflows. Litmus usage analytics are disabled (`policies.monitoring.disabled: true`). The operator tolerates the `chaos.litmuschaos.io/az-failure` taint. The AZ preflight also requires Litmus and Argo workflow pods to be outside the target zone.

### 3. RBAC

- `litmus-pod-mlflow`, `litmus-pod-kserve` and `litmus-pod-argocd` can delete pods only in their target namespace.
- `litmus-stress-mlflow` adds MLflow exec and read-only node access. Stress helpers remain privileged.
- `litmus-node` can patch nodes and evict pods; it is reserved for node/zone experiments.
- `chaos-workflow-mlflow` can inspect MLflow and manage its experiment; `chaos-workflow-node` has the
  cluster read and node cleanup permissions needed by the AZ workflow.
- `litmus-chaos-exporter` is read-only. The operator's direct secret reads are confined to `litmus`.
- `gitops/infrastructure/security/chaos-guardrails.yaml` constrains engine and runner account selection.
  Install these Flux-owned policies before allowing untrusted workflow submissions. The privileged Litmus
  namespace and operator are still administrative components, not tenant isolation boundaries.

## How to run an experiment

### Phase 1 experiments

#### 1. MLflow pod-delete (recommended first experiment)

**Goal**: Prove that deleting one MLflow pod does not cause downtime while at least two replicas are ready. Replica count alone does not prove availability; the probe and post-check determine the result.

```bash
# Verify MLflow is HA first (dev overlay prefixes names with dev-)
kubectl get deployment dev-mlflow-server -n mlflow
# READY should be 2/2

# Run via Argo Workflow (recommended)
argo submit --from workflowtemplate/mlflow-resilience-test -n argo-workflows --watch

# Or run the experiment manually
kubectl apply -f gitops/applications/apps/chaos/experiments/pod-delete-mlflow.yaml
kubectl wait --for=jsonpath='{.status.engineStatus}'=completed chaosengine/mlflow-pod-delete -n litmus --timeout=180s
kubectl get chaosresult mlflow-pod-delete-pod-delete -n litmus -o jsonpath='{.status.experimentStatus.verdict}'
```

The workflow runs: pre-check (replicas + `/health`) → start the probe → pod-delete while probing → wait for engine completion → post-check → log a run through the MLflow REST API → report. Probes pause one second between requests, with a two-second request timeout. Downtime uses elapsed time, not a count of failed requests. It fails if the Litmus verdict is not `Pass` or downtime exceeds `max-acceptable-downtime-seconds` (default 5). The workflow deadline is 10 minutes; the exit handler requests a stop and reports cleanup errors.

Success criteria:
- MLflow `/health` never fails for more than 5 consecutive seconds.
- A new MLflow run can be logged immediately after the experiment.
- The MLflow Deployment returns 2/2 ready replicas.

#### 2. KServe controller pod-delete

**Goal**: Verify that existing `InferenceServices` continue serving when the KServe controller is briefly down.

```bash
kubectl apply -f gitops/applications/apps/chaos/experiments/pod-delete-kserve-controller.yaml
kubectl wait --for=jsonpath='{.status.engineStatus}'=completed chaosengine/kserve-controller-pod-delete -n litmus --timeout=180s
```

Note: The KServe controller has 1 replica, so there is a brief control-plane gap. The data plane (inference pods) is unaffected.

#### 3. ArgoCD application-controller pod-delete

**Goal**: Verify that existing GitOps Applications remain synced while the controller restarts.

```bash
kubectl apply -f gitops/applications/apps/chaos/experiments/pod-delete-argocd-controller.yaml
kubectl wait --for=jsonpath='{.status.engineStatus}'=completed chaosengine/argocd-controller-pod-delete -n litmus --timeout=180s
```

Note: `argocd-application-controller` is a StatefulSet in ArgoCD v2.9 (`appkind: statefulset`).

#### 4. MLflow CPU hog

**Goal**: Stress one MLflow pod and verify the other replica still serves while HPA may scale up.

```bash
kubectl apply -f gitops/applications/apps/chaos/experiments/cpu-hog-mlflow.yaml
kubectl wait --for=jsonpath='{.status.engineStatus}'=completed chaosengine/mlflow-cpu-hog -n litmus --timeout=240s
```

Success criteria:
- One MLflow pod gets CPU-stressed; the other remains healthy.
- HPA may add a 3rd replica if average CPU exceeds 70%.
- After the experiment, MLflow `/health` returns 200.

### Phase 2 experiments

Node-level chaos. Run only in `dev`/`staging`, with at least 2 nodes per node group and nodes in more than one AZ.

#### 2.1 Worker node drain

**Goal**: Pods on a drained node reschedule on other nodes, PDBs are respected and the node group keeps capacity.

Pick a node that does not host the Litmus operator, otherwise the runner can be evicted and the node stays cordoned:

```bash
litmus_nodes=$(kubectl get pods -n litmus -o jsonpath='{.items[*].spec.nodeName}')
kubectl get nodes -l '!nvidia.com/gpu.present' -o name | sed 's|node/||' | grep -vxF -f <(echo "$litmus_nodes" | tr ' ' '\n')

sed "s/REPLACE_WITH_NODE_NAME/<node>/" gitops/applications/apps/chaos/experiments/node-drain-worker.yaml | kubectl apply -f -
kubectl wait --for=jsonpath='{.status.engineStatus}'=completed chaosengine/worker-node-drain -n litmus --timeout=600s
```

Success criteria: evicted pods are Running elsewhere in < 3 min; MLflow and KServe keep serving; the node is uncordoned after 300 s (`kubectl get node <node>` shows no `SchedulingDisabled`).

If the experiment is interrupted: `kubectl uncordon <node>`.

#### 2.2 GPU node drain

**Goal**: GPU training pods fail gracefully and requeue on another GPU node.

```bash
kubectl get nodes -l nvidia.com/gpu.present=true
sed "s/REPLACE_WITH_NODE_NAME/<gpu-node>/" gitops/applications/apps/chaos/experiments/node-drain-gpu.yaml | kubectl apply -f -
```

Requires the GPU node group (`enable_gpu_node_group = true`) and a running GPU training workflow. With a single GPU node, expect the training to stay Pending until the node is uncordoned.

#### 2.3 AZ failure

**Goal**: Evict workloads from every node in one zone and measure service recovery in the remaining zones. This is a taint-based eviction simulation, not an AWS AZ outage: nodes, networking, storage, and taint-tolerating pods remain available.

```bash
kubectl get nodes -L topology.kubernetes.io/zone
argo submit --from workflowtemplate/az-failure-test -n argo-workflows --watch \
  -p zone=<zone> \
  -p confirm-zone-failure=true \
  -p probe-url=http://<inference-service-host>/invocations \
  -p 'probe-body={"dataframe_split":{"columns":["feature"],"data":[[1.0]]}}' \
  -p 'probe-response-filter=.predictions | type == "array" and length == 1'
```

The workflow requires a non-empty probe URL and explicit confirmation. Preflight refuses a target
with no surviving Ready, schedulable node, an existing chaos taint, or Litmus/Argo pods in the target
zone. Workflow pods are scheduled outside that zone. Check spare CPU, memory, GPU capacity and PVC
zone constraints separately; the node check does not prove that workloads will fit.

One `node-taint` ChaosEngine is created per target node, using
`chaos.litmuschaos.io/az-failure=<workflow-name>:NoExecute` for `chaos-duration` seconds (default 300).
The probe starts before injection and runs until all engines complete. Cleanup waits for the engines
to stop before removing residual taints, and only removes taints owned by this workflow.

Success criteria: the probe never fails for more than `max-acceptable-downtime-seconds` (default 10); KServe p95 latency stays < 500 ms in Grafana.

If the workflow is interrupted before the exit handler runs, first stop its ChaosEngines and verify they are completed. Inspect the taint values and remove only the affected workflow's taints:

```bash
kubectl get nodes -l topology.kubernetes.io/zone=<zone> -o json
kubectl taint node <affected-node> chaos.litmuschaos.io/az-failure-
```

#### 2.4 Network partition KServe → MLflow (disabled)

The manifest is parked with `engineState: stop` and requires a specific model label. Do not activate it
until backlog #59 is resolved. The previous `NAMESPACE_SELECTOR=...=mlflow` **allowed** MLflow traffic;
Litmus treats that selector as an allow list. The parked version allows `kube-system` for DNS, but
isolates other destinations too and is not a selective MLflow fault.

Kubernetes NetworkPolicies are additive: an existing policy allowing MLflow remains effective.
Before enabling this experiment, verify CNI policy enforcement and use a disposable model workload
with compatible policies. Prove that MLflow is reachable before the fault, unreachable from that
workload during it, and reachable again after cleanup; probe inference independently throughout.
Do not remove production policies just to make the experiment pass.

References: [Litmus network partition semantics](https://litmuschaos.github.io/litmus/experiments/categories/pods/pod-network-partition/)
and [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

#### EC2 instance stop (deferred)

The proposal's original 2.1 (`ec2-terminate-by-tag`) needs an IRSA dedicated fault role with `ec2:StopInstances`/`ec2:TerminateInstances` on the node group instances, created in Terraform. Tracked as backlog #58. Until then, the node drain experiment covers pod rescheduling.

---

## How to add a new experiment

1. Create a new file under `experiments/` (e.g., `experiments/node-memory-hog.yaml`).
2. Use an experiment name from the `kubernetes-chaos` chart (`kubectl get chaosexperiments -n litmus`).
3. Select the dedicated account with permissions for that fault and set `jobCleanUpPolicy: delete`.
4. Restrict the target with `appinfo` (namespace, label selector, kind) or `TARGET_NODE`.
5. If the experiment needs new API permissions, extend `base/rbac.yaml` and get a security review.
6. Run it manually in `dev` first.
7. Only after it is proven safe, wrap it in a WorkflowTemplate under `workflows/` with pre/post checks, `activeDeadlineSeconds` and an `onExit` cleanup.

### Example template

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: <name>
  namespace: litmus
spec:
  appinfo:
    appns: "<target-namespace>"
    applabel: "<label-selector>"
    appkind: "<deployment|statefulset|daemonset>"
  engineState: "active"
  jobCleanUpPolicy: "delete"
  chaosServiceAccount: litmus-pod-mlflow
  experiments:
    - name: <experiment-name>
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: "60"
            - name: CHAOS_INTERVAL
              value: "10"
```

---

## Environment-specific behavior

| Environment | Validation workflows | Notes |
|-------------|----------------------|-------|
| `dev` | Yes | Start with MLflow pod deletion after preflight checks. |
| `staging` | Yes | Run experiments during business hours with team on call. |
| `prod` | No | **No automated experiments.** Litmus is installed but experiments must be approved and scheduled manually. |

---

## Integration with monitoring

The chaos stack exposes Prometheus metrics via the `litmus-chaos-exporter` Service, backed by the `litmus-chaos-exporter` Deployment in `base/exporter.yaml` (the chart's own exporter is disabled because its Service selects the operator pods too).

### What is already configured

- `gitops/applications/apps/chaos/base/metrics-service.yaml` creates `litmus-chaos-exporter.litmus.svc.cluster.local:8080`.
- `gitops/applications/apps/monitoring/base/configmap.yaml` adds a Prometheus scrape job:

```yaml
- job_name: 'litmus-chaos-exporter'
  static_configs:
    - targets: ['litmus-chaos-exporter.litmus.svc.cluster.local:8080']
  metrics_path: /metrics
  scrape_interval: 15s
```

### Available metrics

- `litmuschaos_passed_experiments`, `litmuschaos_failed_experiments`, `litmuschaos_awaited_experiments`
- `litmuschaos_experiment_verdict` — verdict per ChaosEngine/experiment
- `litmuschaos_cluster_scraped_at` — exporter heartbeat

### Recommended Grafana panels

- Experiment duration
- Pass/fail ratio
- Target service availability during chaos
- KServe latency/error rate
- MLflow run success rate

### Note on ServiceMonitor

This project uses vanilla Prometheus (StatefulSet + ConfigMap) rather than the Prometheus Operator, so `ServiceMonitor` CRDs are not available. If the project later migrates to the Prometheus Operator, replace the static scrape config with a `ServiceMonitor` selecting `app.kubernetes.io/name: litmus-chaos-exporter`.

---

## Common commands

```bash
# Build the dev overlay locally
kustomize build gitops/applications/apps/chaos/overlays/dev

# List running/past chaos engines and results
kubectl get chaosengine,chaosresult -n litmus

# Stop a running experiment
kubectl patch chaosengine <name> -n litmus --type merge -p '{"spec":{"engineState":"stop"}}'

# Check Litmus pods and HelmReleases
kubectl get pods -n litmus
kubectl get helmrelease -n litmus

# List the installed experiment definitions
kubectl get chaosexperiments -n litmus
```

---

## Safety checklist before running any experiment

1. Run only in `dev` or `staging` unless explicitly approved for prod.
2. Ensure MLflow DB and model artifacts are backed up (S3 + PVC).
3. Notify the team in Slack.
4. Have someone on call during the experiment window.
5. Set a short duration (5–15 min) and an abort timer.
6. Do not target `kube-system`, `istio-system`, `gatekeeper-system`, or `litmus` namespaces.
7. Verify the target service has replicas > 1 for pod-delete experiments.
8. For node experiments, verify the target node does not host Litmus pods and that other nodes have spare capacity.

---

## Next steps

1. Deploy the `chaos` application via ArgoCD in `dev` and check `kubectl get chaosexperiments -n litmus`.
2. Run the Phase 1 experiments and `mlflow-resilience-test`; document the observed RTO per service.
3. Validate node drain and zone eviction in dev, including cleanup after a controlled abort.
4. Resolve network isolation (#59) and role separation (#60) before expanding the fault scope.
5. Add the IRSA role for `ec2-terminate-by-tag` (backlog #58).
6. Move to Phase 3: external dependency chaos (S3, ECR, MLflow DB).

---

*For strategic context, phased plan, and SLO prerequisites, see [`docs/chaos-engineering-proposal.md`](../../../../docs/chaos-engineering-proposal.md).*
