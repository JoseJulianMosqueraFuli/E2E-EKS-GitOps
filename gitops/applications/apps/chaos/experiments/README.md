# First chaos experiment: MLflow pod deletion

Start in dev after Litmus, Argo Workflows, and MLflow are healthy. The MLflow Deployment must have at
least two ready replicas. These commands target an existing cluster; no local ML stack is needed.

## Recommended: validated workflow

```bash
argo submit --from workflowtemplate/mlflow-resilience-test -n argo-workflows --watch
```

The workflow checks readiness, starts a health probe before injecting the fault, measures downtime
until the ChaosEngine completes, checks the verdict and recovery, then writes a test run to MLflow.
Its exit handler stops the experiment and reports cleanup failures.

## Manual experiment

```bash
kubectl apply -f gitops/applications/apps/chaos/experiments/pod-delete-mlflow.yaml
kubectl wait --for=jsonpath='{.status.engineStatus}'=completed chaosengine/mlflow-pod-delete -n litmus --timeout=180s
kubectl get chaosresult mlflow-pod-delete-pod-delete -n litmus -o jsonpath='{.status.experimentStatus.verdict}'
```

A manual ChaosEngine does not include the workflow's service availability checks or shared mutex.
Run only one fault at a time. A Litmus `Pass` alone does not prove that MLflow remained usable.

## Other experiments

See the [operational runbook](../README.md) for KServe, ArgoCD, CPU stress, node drain, zone eviction,
prerequisites and manual recovery. The network partition manifest remains **stopped** until the
isolation checks in backlog #59 are implemented. Phase 1–2 still need validation on EKS.
