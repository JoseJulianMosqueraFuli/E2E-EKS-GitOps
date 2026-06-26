# 📚 Documentation Hub — E2E-EKS-GitOps

> **Single entry point for all project documentation.**
> Start here and follow the links. Each topic below names its **canonical source**
> so there is one place to update and no drift between documents.

_Last updated: 2026-06-25_

---

## 🧭 Quick navigation by goal

| I want to...                           | Go to                                                      |
| -------------------------------------- | ---------------------------------------------------------- |
| Understand the whole architecture      | [`implementation.md`](../implementation.md)                |
| Get the project running in 5 minutes   | [`quick-start-guide.md`](quick-start-guide.md)             |
| Work on the ML code locally            | [`ml-platform-guide.md`](ml-platform-guide.md)             |
| Set up GitOps (ArgoCD + Flux)          | [`../gitops/SETUP.md`](../gitops/SETUP.md)                 |
| Configure monitoring & drift detection | [`model-monitoring-guide.md`](model-monitoring-guide.md)   |
| Review security posture & hardening    | [`security-best-practices.md`](security-best-practices.md) |
| See what is pending / the backlog      | [`../backlog.md`](../backlog.md)                           |
| See open critical/high issues          | [`../critical.md`](../critical.md)                         |

---

## 1. Architecture & Overview

| Document                                    | Description                                                                            |
| ------------------------------------------- | -------------------------------------------------------------------------------------- |
| [`implementation.md`](../implementation.md) | **Canonical architecture overview** — stack, repo layout, components, security, CI/CD. |
| [`../README.md`](../README.md)              | Project landing page (English).                                                        |
| [`../README.es.md`](../README.es.md)        | Project landing page (Español).                                                        |

## 2. Getting Started & Guides

| Document                                                 | Description                                           |
| -------------------------------------------------------- | ----------------------------------------------------- |
| [`quick-start-guide.md`](quick-start-guide.md)           | 5-minute setup guide.                                 |
| [`ml-platform-guide.md`](ml-platform-guide.md)           | ML code, pipelines, CLI usage (local-first).          |
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
| [`../infra/README.md`](../infra/README.md)                                   | Terraform infrastructure reference.            |
| [`../gitops/tests/README.md`](../gitops/tests/README.md)                     | GitOps property-based test suite.              |

## 4. Project Status & Backlog

> ⚠️ **Drift control**: these documents overlap by design. Respect the hierarchy below
> to keep a single source of truth and avoid contradictory status across files.

| Document                                                                   | Role                                                                             |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [`../backlog.md`](../backlog.md)                                           | **Canonical backlog** — the full map of pending work (CRITICAL → LOW + roadmap). |
| [`../critical.md`](../critical.md)                                         | Detailed CRITICAL/HIGH findings (CVSS, fix, owner). Sub-view of the backlog.     |
| [`PENDING.md`](PENDING.md)                                                 | Product/roadmap-oriented status checklist. Sub-view of the backlog.              |
| [`../VALIDATION_REPORT.md`](../VALIDATION_REPORT.md)                       | Point-in-time validation report (snapshot, not continuously updated).            |
| [`../gitops/IMPLEMENTATION_STATUS.md`](../gitops/IMPLEMENTATION_STATUS.md) | GitOps-specific implementation status.                                           |
| [`../gitops/TASK_1_SUMMARY.md`](../gitops/TASK_1_SUMMARY.md)               | GitOps Task 1 completion summary (historical record).                            |

---

## 5. Canonical sources (update here, not elsewhere)

| Topic                      | Canonical file                                                                   |
| -------------------------- | -------------------------------------------------------------------------------- |
| Architecture / components  | [`implementation.md`](../implementation.md)                                      |
| Security review & findings | [`implementation.md` §9](../implementation.md) + [`critical.md`](../critical.md) |
| Pending work / backlog     | [`backlog.md`](../backlog.md)                                                    |
| Critical & high issues     | [`critical.md`](../critical.md)                                                  |
| Local ML usage             | [`ml-platform-guide.md`](ml-platform-guide.md)                                   |
| GitOps install             | [`../gitops/SETUP.md`](../gitops/SETUP.md)                                       |

---

_When adding a new document, register it here under the right section and, if it tracks
status, link it back to `backlog.md` as the canonical source._
