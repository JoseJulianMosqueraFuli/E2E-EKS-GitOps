# Chaos Engineering Proposal - E2E-EKS-GitOps

**Scope**: MLOps platform running on Amazon EKS (MLflow, KServe, Kubeflow, ArgoCD, Prometheus/Grafana, Istio, S3/ECR/Glue).
**Status**: Proposal — not yet implemented.
**Last updated**: 2026-07-13

---

## 1. Goal

Validate that the ML pipeline (train → register → deploy → monitor) survives real-world failures: node loss, pod crashes, network partitions, dependency outages, and AZ failures. The objective is not to break things for fun, but to discover weak points before production and define recovery SLAs.

---

## 2. Recommended Tool

**LitmusChaos** (installed via Helm and managed by GitOps).

Why LitmusChaos:
- Prebuilt AWS experiments: `ec2-stop-by-id`, `ebs-loss`, `aws-ssm-chaos`.
- Native Kubernetes experiments: `pod-delete`, `node-drain`, `network-partition`, `cpu-hog`, `memory-hog`.
- Prometheus metrics integration (we already have Prometheus/Grafana).
- Workflow-based experiments (can chain multiple failure modes).
- Can be deployed as an ArgoCD application, consistent with the project's GitOps model.

Alternative: **Chaos Mesh** if you prefer a lighter CNCF project, but Litmus has better AWS-native coverage.

---

## 3. Phased Adoption

### Phase 1 — Single Pod/Service Chaos (Week 1)

Scope: One pod at a time in `dev`. Validate Kubernetes rescheduling and service recovery.

| # | Experiment | Target | Success Criteria |
|---|------------|--------|------------------|
| 1.1 | Pod delete | `mlflow-server` deployment | Pod reschedules in < 2 min; new MLflow runs keep logging. |
| 1.2 | Pod delete | `kserve-controller-manager` | Existing InferenceServices continue serving (controller is not in data path). |
| 1.3 | Pod delete | `argocd-application-controller` | GitOps sync continues after recovery. |
| 1.4 | CPU/memory hog | `mlflow-server` pod | HPA scales or pod is evicted; no persistent `CrashLoopBackOff`. |

**Metrics**: RTO < 2 min for control-plane services; no metric gaps > 5 min in Prometheus.

### Phase 2 — Node and Infrastructure Chaos (Week 2–3)

Scope: Worker nodes, GPU nodes, and AZ-level failures.

| # | Experiment | Target | Success Criteria |
|---|------------|--------|------------------|
| 2.1 | EC2 stop | One worker node via `ec2-stop-by-id` | Cluster autoscaler adds a new node in < 3 min; pods reschedule. |
| 2.2 | GPU node loss | One GPU node | GPU trainings fail gracefully and requeue on the next available GPU node. |
| 2.3 | AZ failure | Taint all nodes in one AZ | KServe serving continues via Istio locality failover; no p95 latency > 500 ms. |
| 2.4 | Network partition | Block traffic between `mlflow` and `kserve` namespaces | Inference services do not depend on MLflow at runtime; failure is controlled. |

**Metrics**: Autoscaler reaction < 3 min; KServe p95 latency < 500 ms during node chaos.

### Phase 3 — External Dependency Chaos (Week 4)

Scope: AWS services and data stores that the platform depends on.

| # | Experiment | Target | Success Criteria |
|---|------------|--------|------------------|
| 3.1 | S3 latency/availability | Artifact store for MLflow | Pipelines fail gracefully; no model corruption; retries with backoff. |
| 3.2 | ECR unavailable | Image registry | New training jobs do not hang indefinitely; clear error message. |
| 3.3 | MLflow DB outage | Postgres/RDS for MLflow tracking | Tracking resumes after DB recovery; no unrecoverable state. |
| 3.4 | Glue crawler failure | Data catalog | Training pipeline does not block if catalog is stale. |

**Metrics**: Exponential backoff present; circuit breaker or dead-letter for failed jobs; actionable alerts.

### Phase 4 — End-to-End ML Pipeline Chaos (Week 5+)

Scope: ML-specific failure modes across the full lifecycle.

| # | Experiment | Target | Success Criteria |
|---|------------|--------|------------------|
| 4.1 | Data drift injection | Inference traffic | Evidently detects drift in < 15 min; auto-retraining workflow triggers. |
| 4.2 | Feature store outage | Feast online store | Inference falls back to offline features or default values. |
| 4.3 | Corrupt model upload | MLflow model registry | KServe readiness/health checks reject the model before routing traffic. |
| 4.4 | GitOps desync | Manual change outside Git | ArgoCD/Flux detects drift and reverts in < 5 min. |

**Metrics**: Drift detection < 15 min; GitOps convergence < 5 min; corrupt model rejected.

---

## 4. Integration with Existing Components

| Existing Component | Role in Chaos Engineering |
|--------------------|---------------------------|
| Prometheus + Grafana | Dashboards for "during-chaos" metrics: KServe latency, error rate, pod scheduling, autoscaler activity. |
| ArgoCD / Flux | Deploy Litmus and chaos experiments as GitOps applications. |
| Argo Workflows | Orchestrate chaos experiment + validation + notification workflows. |
| Slack / Teams | Send start/end/alert notifications. |
| Gatekeeper | Ensure security policies remain enforced during chaos. |
| Istio | Fault injection (delay/abort) without killing pods. |

---

## 5. Canonical Experiment Template

```yaml
# gitops/applications/apps/chaos/experiments/pod-delete-mlflow.yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: mlflow-pod-delete
  namespace: litmus
spec:
  appinfo:
    appns: 'mlflow'
    applabel: 'app=mlflow-server'
    appkind: 'deployment'
  experiments:
    - name: pod-delete
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: '60'
            - name: CHAOS_INTERVAL
              value: '10'
            - name: FORCE
              value: 'false'
```

---

## 6. Automation Proposal

A nightly Argo Workflow in `dev` or `staging`:

1. **Pre-check**: smoke tests against MLflow and KServe.
2. **Run experiment**: Litmus ChaosEngine (e.g., pod-delete MLflow).
3. **Post-check**: repeat smoke tests; query Prometheus for SLO metrics.
4. **Report**: publish result to Slack/Teams.
5. **Abort**: stop the workflow if recovery exceeds 10 minutes.

```text
Smoke tests → Chaos experiment → Smoke tests → Prometheus SLO check → Slack report
```

---

## 7. Safety Guardrails

- **Environments**: Only `dev` and `staging` until SLOs are mature. Never run unreviewed experiments in `prod`.
- **Duration**: Keep experiments between 5 and 15 minutes.
- **Auto-rollback**: Abort if the cluster does not recover within 10 minutes.
- **Exclusions**: Do not target `kube-system`, `istio-system`, `gatekeeper-system`, or `litmus` namespaces in Phase 1.
- **Backups**: Back up MLflow DB before dependency-chaos experiments.
- **Scheduling**: Run during business hours with the team on call.
- **Cost control**: Node-termination experiments will trigger autoscaling; budget for extra EC2 hours during tests.

---

## 8. First Experiment to Run

This is the smallest experiment that validates the most important assumption: *MLflow can survive a pod restart without losing data or breaking the ML pipeline.*

1. Install LitmusChaos in `dev` via Helm (or as a GitOps application).
2. Deploy the `pod-delete-mlflow` experiment above.
3. Run a script that logs one MLflow run every 10 seconds.
4. Watch Grafana: verify pod rescheduling and run continuity.
5. Document RTO and any data loss.

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss if MLflow uses local storage | Ensure MLflow uses PVC + S3 before running pod-delete. |
| Runaway autoscaling costs | Limit experiments to 15 min; use spot instances for dev chaos nodes. |
| False-positive alerts | Mute non-actionable alerts during scheduled chaos windows. |
| Team disruption | Run in a dedicated dev environment; publish schedule in advance. |
| No clear pass/fail criteria | Define SLOs first (see Section 10). |

---

## 10. Prerequisites Before Starting

1. **Define SLOs**: e.g., KServe p99 latency < 200 ms, MLflow RTO < 2 min, ArgoCD sync success rate > 99%.
2. **Mature observability**: Ensure all services export metrics and have Grafana dashboards.
3. **Backup strategy**: MLflow DB and model artifacts must be recoverable.
4. **On-call rotation**: Someone must be available to stop experiments if needed.
5. **GitOps ready**: Litmus and experiments must be deployable via ArgoCD.

---

## 11. Next Steps

| Step | Owner | Effort |
|------|-------|--------|
| Approve proposal and pick target environment | Platform Lead | 30 min |
| Add Litmus Helm chart to `gitops/applications/apps/chaos/` | DevOps | 2h |
| Create first experiment: `pod-delete-mlflow` | DevOps | 1h |
| Add Grafana dashboard for chaos metrics | Platform | 2h |
| Define SLOs and pass/fail criteria | SRE + ML | 2h |
| Run first experiment and document RTO | DevOps + ML | 2h |

---

*Document generated as a proposal. Implement only after SLOs and backups are in place.*
