# Chaos Engineering Stack — Internal Runbook

**Application**: `chaos`  
**Namespace**: `litmus`  
**Tool**: LitmusChaos  
**Deployed via**: ArgoCD ApplicationSet `mlops-applications`  
**High-level proposal**: see [`docs/chaos-engineering-proposal.md`](../../docs/chaos-engineering-proposal.md)

---

## What this directory contains

```
gitops/applications/apps/chaos/
├── base/
│   ├── kustomization.yaml      # Base Kustomize manifest
│   ├── namespace.yaml          # litmus namespace (privileged PSS)
│   ├── litmus.yaml             # HelmRepository + HelmRelease for Litmus
│   └── rbac.yaml               # ClusterRole, ClusterRoleBinding, ServiceAccount
├── overlays/
│   ├── dev/                    # Dev overlay (just labels today)
│   ├── staging/                # Staging overlay
│   └── prod/                   # Prod overlay (includes warning comment)
└── experiments/
    ├── README.md               # Manual runbook for the first experiment
    └── pod-delete-mlflow.yaml  # First experiment: kill MLflow pods
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

Marked with `pod-security.kubernetes.io/enforce: privileged` because Litmus experiment pods need elevated privileges to run faults (e.g., network partitions, node-level chaos).

### 2. HelmRelease (`litmus`)

Uses the upstream chart from `https://litmuschaos.github.io/litmus-helm/`, version `3.16.x`.

Key values:
- `portal.server.enabled: false` — we do not run the Litmus web UI by default. Experiments are submitted via `kubectl` or Argo Workflows.
- `mongodb.enabled: true` with an 8Gi PVC — persistence for experiment metadata.
- `agent.enabled: true`, `selfDeployer: true` — the chaos agent runs in the same namespace and can deploy experiment runners.

### 3. RBAC

A dedicated `ServiceAccount` `litmus-admin` in the `litmus` namespace bound to a `ClusterRole` that allows:
- Read/write pods, nodes, deployments, statefulsets, daemonsets, replicasets, jobs, cronjobs across the cluster.
- Manage Litmus CRDs: `ChaosEngine`, `ChaosExperiment`, `ChaosResult`.
- Read ArgoCD applications (for future GitOps-related chaos experiments).

⚠️ This is a powerful role. Do not change it without a security review.

---

## How to run an experiment

### Phase 1 experiments

#### 1. MLflow pod-delete (recommended first experiment)

**Goal**: Prove that deleting one MLflow pod does not cause downtime because the Deployment runs with 2 replicas.

```bash
# Verify MLflow is HA first
kubectl get deployment mlflow-server -n mlflow
# READY should be 2/2

# Run via Argo Workflow (recommended)
kubectl apply -f gitops/applications/apps/chaos/workflows/mlflow-resilience-test.yaml
argo submit --watch gitops/applications/apps/chaos/workflows/mlflow-resilience-test.yaml -n argo-workflows

# Or run the experiment manually
kubectl apply -f gitops/applications/apps/chaos/experiments/pod-delete-mlflow.yaml
kubectl wait --for=condition=EngineCompleted chaosengine/mlflow-pod-delete -n litmus --timeout=120s
kubectl get chaosresults -n litmus
```

Success criteria:
- MLflow `/health` never fails for more than 5 consecutive seconds.
- A new MLflow run can be logged immediately after the experiment.
- `kubectl get deployment mlflow-server -n mlflow` returns 2/2 replicas.

#### 2. KServe controller pod-delete

**Goal**: Verify that existing `InferenceServices` continue serving when the KServe controller is briefly down.

```bash
kubectl apply -f gitops/applications/apps/chaos/experiments/pod-delete-kserve-controller.yaml
kubectl wait --for=condition=EngineCompleted chaosengine/kserve-controller-pod-delete -n litmus --timeout=120s
```

Note: The KServe controller has 1 replica, so there is a brief control-plane gap. The data plane (inference pods) is unaffected.

#### 3. ArgoCD application-controller pod-delete

**Goal**: Verify that existing GitOps Applications remain synced while the controller leader re-elects.

```bash
kubectl apply -f gitops/applications/apps/chaos/experiments/pod-delete-argocd-controller.yaml
kubectl wait --for=condition=EngineCompleted chaosengine/argocd-controller-pod-delete -n litmus --timeout=120s
```

Note: ArgoCD application-controller uses leader election. Expect a short leader re-election pause.

#### 4. MLflow CPU hog

**Goal**: Stress one MLflow pod and verify the other replica still serves while HPA may scale up.

```bash
kubectl apply -f gitops/applications/apps/chaos/experiments/cpu-hog-mlflow.yaml
kubectl wait --for=condition=EngineCompleted chaosengine/mlflow-cpu-hog -n litmus --timeout=180s
```

Success criteria:
- One MLflow pod gets CPU-stressed; the other remains healthy.
- HPA may add a 3rd replica if average CPU exceeds 70%.
- After the experiment, MLflow `/health` returns 200.

---

## How to add a new experiment

1. Create a new file under `experiments/` (e.g., `experiments/node-drain-worker.yaml`).
2. Use the `ChaosEngine` CRD. Reference Litmus docs for available experiments:
   - `pod-delete`
   - `node-drain`
   - `network-partition`
   - `cpu-hog`
   - `memory-hog`
   - `disk-fill`
   - AWS-specific experiments (require additional IAM permissions)
3. Set `chaosServiceAccount: litmus-admin`.
4. Restrict the target with `appinfo` (namespace, label selector, kind).
5. Add a manual README if the experiment is non-trivial.
6. Run it manually in `dev` first.
7. Only after it is proven safe, consider adding it to an Argo Workflow for automation.

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
  chaosServiceAccount: litmus-admin
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

| Environment | Auto-sync | Notes |
|-------------|-----------|-------|
| `dev` | Yes | Safe to run experiments manually. |
| `staging` | Yes | Run experiments during business hours with team on call. |
| `prod` | Yes | **No automated experiments.** Litmus is installed but experiments must be approved and scheduled manually. |

The prod overlay contains a comment warning that chaos experiments require mature SLOs and on-call coverage before enabling.

---

## Integration with monitoring

The chaos stack exposes Prometheus metrics via the `litmus-chaos-exporter` Service.

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

After deploying, Prometheus will expose metrics such as:

- `chaos_engine_status` — current state of each ChaosEngine
- `chaos_experiment_status` — status per experiment
- `chaos_result_verdict` — pass/fail summary of each ChaosResult

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
kubectl kustomize gitops/applications/apps/chaos/overlays/dev

# List running/past chaos engines
kubectl get chaosengine -n litmus

# List chaos results
kubectl get chaosresult -n litmus

# Delete an experiment
kubectl delete chaosengine <name> -n litmus

# Check Litmus agent pods
kubectl get pods -n litmus

# Check HelmRelease status
kubectl get helmrelease -n litmus
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

---

## Next steps

1. Deploy the `chaos` application via ArgoCD in `dev`.
2. Verify Litmus pods are running.
3. Run all Phase 1 experiments and confirm expected behavior:
   - `mlflow-resilience-test.yaml` → PASS
   - `pod-delete-kserve-controller.yaml` → inference still works
   - `pod-delete-argocd-controller.yaml` → apps stay synced
   - `cpu-hog-mlflow.yaml` → HPA reacts, no downtime
4. Document observed RTO for each target service.
5. Move to Phase 2: node-drain and network-partition experiments.

---

*For strategic context, phased plan, and SLO prerequisites, see [`docs/chaos-engineering-proposal.md`](../../docs/chaos-engineering-proposal.md).*
