---
description: "MLOps architecture - lifecycle, components, contracts between training, registry, serving and monitoring"
applyTo: "**"
---

# ML Platform Architecture

## Lifecycle and owning component

| Stage | Component | Location |
|-------|-----------|----------|
| Data ingestion & catalog | S3 + Glue | `infra/modules/s3`, `infra/modules/glue` |
| Data validation & features | `ml-platform/src/data`, Feast | `ml-platform/feature_repo/`, `gitops/applications/apps/feast/` |
| Orchestration | Kubeflow Pipelines / Argo Workflows | `gitops/applications/apps/kubeflow/`, `argo-workflows/` |
| Experiment tracking & registry | MLflow (RDS/Postgres backend + S3 artifacts) | `gitops/applications/apps/mlflow/` |
| Serving | KServe | `gitops/applications/apps/kserve/` |
| Monitoring (system + model) | Prometheus/Grafana + drift detection (Evidently) | `gitops/applications/apps/monitoring/`, `ml-platform/src/monitoring/` |

Keep these responsibilities separated; do not, for example, make the serving layer read raw training data.

## Core principles

- **Reproducibility**: every model version must be traceable to code commit, data version/snapshot, feature definitions, hyperparameters and environment (image digest / `poetry.lock`). Log all of it to MLflow.
- **Registry as the contract**: training publishes to the MLflow Model Registry; serving deploys only registered versions referenced by stage/alias. Never deploy from a local path or an ad-hoc run.
- **Training/serving parity**: the same feature transformations must run in training and inference (shared code in `ml-platform/src/data` / Feast feature views). Duplicated feature logic is a bug waiting to happen (training-serving skew).
- **Immutable artifacts**: models, datasets and images are versioned and never overwritten in place.
- **Promotion by gates**: a model is promoted only after automated checks pass — evaluation metrics vs. the current production baseline, data validation, bias/fairness checks where relevant, and a smoke test of the inference endpoint.

## Serving

- Progressive delivery: KServe canary (`canaryTrafficPercent`) or shadow traffic before full rollout; automatic rollback on error rate / latency SLO breach.
- Define SLOs per model (p95 latency, error rate, availability) and alert on them.
- Size requests/limits from load tests; use scale-to-zero in dev, min replicas ≥ 2 in prod.
- Input schema validation at the endpoint; reject rather than silently coerce.

## Monitoring and feedback loop

- Monitor three levels: infrastructure (CPU/GPU/memory), service (latency, throughput, errors), model (data drift, prediction drift, performance against ground truth when labels arrive).
- Drift detection runs on a schedule (`run_drift_check.py`) and exports metrics to Prometheus; alerts route to the owning team.
- Retraining is triggered by policy (drift threshold, performance decay, schedule), runs through the same pipeline, and goes through the same promotion gates. No manual retrain-and-push.
- Log predictions (with request IDs, without PII) to enable offline evaluation and debugging.

## Maturity target

Aim for MLOps level 2 (Google) / automated CI/CD/CT: pipelines as code, automated training on triggers, automated validation and deployment through GitOps. When proposing changes, state which part of this target they advance.
