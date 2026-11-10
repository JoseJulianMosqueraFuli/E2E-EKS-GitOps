# GitOps

Flux manages cluster infrastructure; ArgoCD manages platform and ML applications.
Application manifests live in `applications/apps/<app>/base/`, with environment overlays.
The [project backlog](../docs/project/backlog.md) tracks readiness and pending EKS verification.

## Layout

| Path | Purpose |
|---|---|
| [infrastructure/](infrastructure/README.md) | Flux controllers, sources, cluster add-ons, networking and security |
| [applications/](applications/README.md) | ArgoCD projects, ApplicationSet, application bases and overlays |
| [charts/](charts/README.md) | MLflow, KServe, Kubeflow Pipelines and monitoring charts |
| [platform/](platform/README.md) | AWS account and region configuration |
| `scripts/` | Controller installation, validation and environment promotion |
| [tests/](tests/README.md) | Unit, property and integration tests |

## Validate a change

From the repository root:

```bash
cd gitops
poetry install --with test,dev
poetry run pytest tests/ -m "not integration" -q
```

Poetry uses `package-mode = false`; keep `poetry.lock` versioned. See the
[dependency guide](POETRY_GUIDE.md) for installation groups and updates.
Integration tests require a configured cluster. GitHub Actions runs the
[kind E2E workflow](../.github/workflows/e2e-kind.yml); no local cluster is required.

## Deploy and operate

Follow the [setup guide](SETUP.md) for prerequisites, controller installation, ArgoCD access,
verification, troubleshooting and backups. Configure [AWS placeholders](platform/README.md)
before rendering environment overlays.

- [Runtime configuration and recovery](../docs/architecture/platform-runtime-config.md).
- [Application management](applications/README.md).
- [Current priorities and deployment gates](../docs/project/backlog.md).
- [Historical foundation milestones](../docs/reports/gitops-foundation.md).
