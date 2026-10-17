# 📚 Documentation Hub — E2E-EKS-GitOps

> **Single entry point for all project documentation.**
> Start here and follow the links. Each topic below names its **canonical source**
> so there is one place to update and no drift between documents.

_Last updated: 2026-10-17_

## Documentation layout

| Directory | Contents |
|-----------|----------|
| `architecture/` | Platform architecture and implementation overview |
| `project/` | Canonical backlog and CRITICAL/HIGH findings |
| `reports/` | Historical validation reports |
| `proposals/` | Proposed future work |
| `diagrams/` | Architecture diagram previews |
| `docs/` (this directory) | Documentation index, operational guides, and reference material |

The repository root keeps `README.md`, `README.es.md`, `SECURITY.md`, `AGENTS.md`, and `CLAUDE.md`.
Component-specific documentation stays next to its code in `gitops/`, `k8s/`, and `ml-platform/`.

---

## 🧭 Quick navigation by goal

| I want to...                           | Go to                                                      |
| -------------------------------------- | ---------------------------------------------------------- |
| Understand the whole architecture      | [`architecture/implementation.md`](architecture/implementation.md)                |
| Get the project running in 5 minutes   | [`quick-start-guide.md`](quick-start-guide.md)             |
| Work on the ML code locally            | [`ml-platform-guide.md`](ml-platform-guide.md)             |
| Run / extend the training pipeline     | [`../k8s/mlops-stack/argo-workflows/README.md`](../k8s/mlops-stack/argo-workflows/README.md) |
| Understand the E2E smoke test (CI)     | [`../scripts/e2e/kind-smoke.sh`](../scripts/e2e/kind-smoke.sh) + [`.github/workflows/e2e-kind.yml`](../.github/workflows/e2e-kind.yml) |
| Validate Terraform and run initial AWS plans in GitHub Actions | [`terraform-ci.md`](terraform-ci.md) |
| Configure AI agents (rules, MCP)       | [`../.agents/README.md`](../.agents/README.md)             |
| Set up GitOps (ArgoCD + Flux)          | [`../gitops/SETUP.md`](../gitops/SETUP.md)                 |
| Configure monitoring & drift detection | [`model-monitoring-guide.md`](model-monitoring-guide.md)   |
| Review security posture & hardening    | [`security-best-practices.md`](security-best-practices.md) |
| See what is pending / the backlog      | [`project/backlog.md`](project/backlog.md)                           |
| See open critical/high issues          | [`project/critical.md`](project/critical.md)                         |

---

## 1. Architecture & Overview

| Document                                    | Description                                                                            |
| ------------------------------------------- | -------------------------------------------------------------------------------------- |
| [`architecture/implementation.md`](architecture/implementation.md) | **Canonical architecture overview** — stack, repo layout, components, security, CI/CD. |
| [`architecture.drawio`](architecture.drawio) | Diagrama editable con íconos oficiales AWS y Kubernetes: arquitectura AWS, plataforma en EKS, flujo ML sobre servicios AWS, GitOps por ambiente y componentes Python. |
| [Vista previa SVG](diagrams/architecture-01.svg) | Arquitectura AWS; vistas [EKS](diagrams/architecture-02.svg), [flujo ML en AWS](diagrams/architecture-03.svg), [GitOps](diagrams/architecture-04.svg) y [Python](diagrams/architecture-05.svg). |
| [`../README.md`](../README.md)              | Project landing page (English).                                                        |
| [`../README.es.md`](../README.es.md)        | Project landing page (Español).                                                        |

## 2. Getting Started & Guides

| Document                                                 | Description                                           |
| -------------------------------------------------------- | ----------------------------------------------------- |
| [`quick-start-guide.md`](quick-start-guide.md)           | 5-minute setup guide.                                 |
| [`ml-platform-guide.md`](ml-platform-guide.md)           | ML code, pipelines, CLI usage (local-first).          |
| [`terraform-ci.md`](terraform-ci.md)                    | Terraform validation and initial plans on GitHub-hosted runners. |
| [`model-monitoring-guide.md`](model-monitoring-guide.md) | Evidently drift detection + Grafana monitoring setup. |
| [`../gitops/README.md`](../gitops/README.md)             | GitOps architecture (Flux + ArgoCD).                  |
| [`../gitops/SETUP.md`](../gitops/SETUP.md)               | GitOps installation steps.                            |
| [`../gitops/POETRY_GUIDE.md`](../gitops/POETRY_GUIDE.md) | Poetry workflow for the GitOps tooling.               |

## 3. Reference & Deep Dives

| Document                                                                     | Description                                    |
| ---------------------------------------------------------------------------- | ---------------------------------------------- |
| [`security-best-practices.md`](security-best-practices.md)                   | mTLS, Gatekeeper, IRSA, Pod Security guidance. |
| [`mlops-enterprise-recommendations.md`](mlops-enterprise-recommendations.md) | Production-grade recommendations.              |
| [`PHASE2_IMPLEMENTATION_GUIDE.md`](PHASE2_IMPLEMENTATION_GUIDE.md)           | Phase 2 implementation roadmap.                |
| [`chaos-engineering-proposal.md`](chaos-engineering-proposal.md)             | Chaos engineering proposal (Litmus).           |
| [`proposals/resilience-recovery.md`](proposals/resilience-recovery.md)                             | Resilience & recovery proposal (reference run + failure experiments). |
| [`cost-estimation.md`](cost-estimation.md)                                   | AWS cost estimation (`us-east-1`).             |
| [`../gitops/tests/README.md`](../gitops/tests/README.md)                     | GitOps property-based test suite.              |
| [`../.agents/README.md`](../.agents/README.md)                               | AI agent rules + read-only MCP servers (Kiro, VS Code, Claude Code). |

## 4. Project Status & Backlog

> ⚠️ **Drift control**: these documents overlap by design. Respect the hierarchy below
> to keep a single source of truth and avoid contradictory status across files.

| Document                                                                   | Role                                                                             |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [`project/backlog.md`](project/backlog.md)                                           | **Canonical backlog** — the full map of pending work (CRITICAL → LOW + roadmap). |
| [`project/critical.md`](project/critical.md)                                         | Detailed CRITICAL/HIGH findings (CVSS, fix, owner). Sub-view of the backlog.     |
| [`reports/validation-report.md`](reports/validation-report.md)                       | Point-in-time validation report (snapshot, not continuously updated).            |
| [`repository-audit-report.md`](repository-audit-report.md)                 | Repository audit (snapshot, 2026-10-01).                                         |
| [`../gitops/IMPLEMENTATION_STATUS.md`](../gitops/IMPLEMENTATION_STATUS.md) | GitOps-specific implementation status.                                           |
| [`../gitops/TASK_1_SUMMARY.md`](../gitops/TASK_1_SUMMARY.md)               | GitOps Task 1 completion summary (historical record).                            |

---

## 5. Canonical sources (update here, not elsewhere)

| Topic                      | Canonical file                                                                   |
| -------------------------- | -------------------------------------------------------------------------------- |
| Architecture / components  | [`architecture/implementation.md`](architecture/implementation.md)                                      |
| Security review & findings | [`architecture/implementation.md` §9](architecture/implementation.md) + [`project/critical.md`](project/critical.md) |
| Pending work / backlog     | [`project/backlog.md`](project/backlog.md)                                                    |
| Critical & high issues     | [`project/critical.md`](project/critical.md)                                                  |
| Local ML usage             | [`ml-platform-guide.md`](ml-platform-guide.md)                                   |
| GitOps install             | [`../gitops/SETUP.md`](../gitops/SETUP.md)                                       |
| Chaos engineering proposal | [`chaos-engineering-proposal.md`](chaos-engineering-proposal.md)                 |
| AWS cost estimation        | [`cost-estimation.md`](cost-estimation.md)                                       |
| AI agent rules             | [`../.agents/rules/`](../.agents/rules/) (generated copies are not edited)       |
| AWS account / region       | [`../gitops/platform/README.md`](../gitops/platform/README.md) (`aws.env`, not in git) + Terraform variables |

---

_When adding a new document, register it here under the right section and, if it tracks
status, link it back to `docs/project/backlog.md` as the canonical source._
