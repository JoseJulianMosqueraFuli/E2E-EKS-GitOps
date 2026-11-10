# GitOps foundation: historical record

[Documentation index](../README.md) · [Current backlog](../project/backlog.md)

Consolidated from the initial task summary (January 2026) and implementation status
(updated through June 2026). This records work reported at that time, not a verified EKS deployment.

## Scope delivered

- Repository structure separating Flux infrastructure from ArgoCD applications, with environment overlays.
- Controller installation script, RBAC configuration and health checks.
- ArgoCD AppProject and ApplicationSet for MLOps and platform applications.
- Helm charts for MLflow, KServe, Kubeflow Pipelines and monitoring.
- Python tooling managed with Poetry, plus pytest and Hypothesis tests.
- Environment promotion scripts and pipeline configuration.

The original task mapped requirements 1.1–1.5 to ArgoCD, Flux, RBAC, UI access and repository
connectivity. Controller property tests covered health, replica consistency and stability,
with at least 100 examples configured. These were reported implementation checks; the
current backlog distinguishes static checks, kind validation and pending EKS verification.

## Milestones

| Date | Recorded change |
|---|---|
| January 2026 | Initial foundation and controller health tests |
| 2026-05-16 | Application structure, charts, tests and promotion pipeline |
| 2026-05-19 | Slack notifications, retraining and A/B workflow templates, environment hardening |
| 2026-05-20 | Pending work consolidated in the project backlog |
| 2026-05-31 | Repository diagrams refreshed |
| 2026-06-26 | Application bases and overlays consolidated under `gitops/applications/apps/` |

## Maintained references

Installation commands, file inventories and pending-task lists are maintained in their owning guides:

- [GitOps overview](../../gitops/README.md) and [setup](../../gitops/SETUP.md).
- [Application management](../../gitops/applications/README.md) and [Helm charts](../../gitops/charts/README.md).
- [Python dependencies](../../gitops/POETRY_GUIDE.md) and [tests](../../gitops/tests/README.md).
- [Current priorities](../project/backlog.md) and [security findings](../project/critical.md).

The original references to active Jenkins CI, separate test dependency files and production
readiness are historical. GitHub Actions is the active CI provider; current dependency declarations
live in `gitops/pyproject.toml` and `gitops/poetry.lock`.
