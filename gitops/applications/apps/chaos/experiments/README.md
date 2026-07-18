# First Chaos Experiment — pod-delete on MLflow

**Environment**: dev (only)  
**Goal**: Verify that the `mlflow-server` pod reschedules and continues accepting new runs after deletion.  
**Duration**: 60 seconds  
**Interval**: 10 seconds between deletions

---

## Manual run

```bash
kubectl apply -f gitops/applications/apps/chaos/experiments/pod-delete-mlflow.yaml
```

Watch the result:

```bash
kubectl wait --for=condition=EngineCompleted chaosengine/mlflow-pod-delete -n litmus --timeout=120s
kubectl get chaosresults -n litmus
```

## Steady-state validation

While the experiment runs, execute:

```bash
# In another terminal
cd ml-platform
poetry run python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
for i in range(20):
    with mlflow.start_run():
        mlflow.log_param('index', i)
        mlflow.log_metric('value', i * 0.1)
    print(f'Run {i} logged')
"
```

Success: all 20 runs are visible in the MLflow UI after the experiment ends.

---

*This experiment is intentionally simple. Use it to confirm that the Litmus
operator is installed and that basic pod-kill chaos works before moving to
node-level or dependency-level experiments.*
