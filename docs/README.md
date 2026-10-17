# Documentation

[English overview](../README.md) · [Resumen en español](../README.es.md)

Choose a topic below. Guides contain the implementation details; the
[backlog](project/backlog.md) is the source of truth for current priorities and deployment readiness.
Guides are available in English or Spanish, depending on the topic.

## Start here

| Goal | Guide |
|---|---|
| Validate Terraform and run initial AWS plans in GitHub Actions | [Terraform CI](terraform-ci.md) |
| Understand the platform and repository layout | [Architecture](architecture/implementation.md) |
| Contribute a change and choose the right checks | [Contributing](contributing.md) |
| Explore the ML code locally (optional) | [ML setup](../ml-platform/README.md) · [Training examples](quick-start-guide.md) |

## Build and operate

| Topic | Guides and implementation |
|---|---|
| ML models, pipelines, and CLI | [ML platform guide](ml-platform-guide.md) |
| Training orchestration | [Argo Workflows](../k8s/mlops-stack/argo-workflows/README.md) |
| E2E training test in CI | [Workflow](../.github/workflows/e2e-kind.yml) · [Smoke test script](../scripts/e2e/kind-smoke.sh) |
| GitOps | [Overview](../gitops/README.md) · [Installation](../gitops/SETUP.md) |
| AWS account and region | [Platform configuration](../gitops/platform/README.md) |
| Monitoring and drift detection | [Monitoring guide](model-monitoring-guide.md) |
| Security | [Hardening guide](security-best-practices.md) · [Vulnerability reporting](../SECURITY.md) |
| AWS costs | [Cost estimates](cost-estimation.md) |
| Optional GPU workloads | [GPU Operator](../gitops/applications/apps/gpu-operator/README.md) |
| Chaos experiments | [Litmus setup](../gitops/applications/apps/chaos/README.md) · [Experiments](../gitops/applications/apps/chaos/experiments/README.md) |

## Development reference

- [GitOps Python tooling and Poetry](../gitops/POETRY_GUIDE.md)
- [GitOps test suite](../gitops/tests/README.md)
- [Make commands](../Makefile) and [CI workflows](../.github/workflows/)
- [Agent instructions](../AGENTS.md), [agent configuration](../.agents/README.md), and [canonical rules shared by all agents](../.agents/rules/)

## Architecture diagrams

[Editable diagram](architecture.drawio) and previews:
[AWS](diagrams/architecture-01.svg) · [EKS](diagrams/architecture-02.svg) ·
[ML flow](diagrams/architecture-03.svg) · [GitOps](diagrams/architecture-04.svg) · [Python](diagrams/architecture-05.svg).

## Project status

- [Backlog](project/backlog.md): canonical record of completed and pending work.
- [Critical and high findings](project/critical.md): detailed issues tracked in the backlog.
- [GitOps implementation status](../gitops/IMPLEMENTATION_STATUS.md): component details; check the backlog for current priorities.

## Proposals and historical reports

These provide design context and past findings. They do not establish current deployment readiness.

| Document | Purpose |
|---|---|
| [Enterprise recommendations](mlops-enterprise-recommendations.md) | Production readiness recommendations |
| [Phase 2 guide](PHASE2_IMPLEMENTATION_GUIDE.md) | Implementation roadmap |
| [Chaos engineering](chaos-engineering-proposal.md) | Design and rollout plan |
| [Resilience and recovery](proposals/resilience-recovery.md) | Proposed recovery experiments |
| [Validation report](reports/validation-report.md) | Historical validation snapshot |
| [Repository audit](repository-audit-report.md) | Historical audit snapshot |
| [GitOps task summary](../gitops/TASK_1_SUMMARY.md) | Historical implementation record |

## Maintaining these docs

Keep the public READMEs brief and aligned in English and Spanish; link to detailed guides here.
Update each topic in its existing guide instead of duplicating it. Register new documents in this index.
Store architecture, project tracking, reports, and proposals in their matching subdirectories.
Component documentation stays beside its code. See [documentation placement](../AGENTS.md#documentation-placement).
