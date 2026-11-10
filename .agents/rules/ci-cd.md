---
description: CI/CD pipelines (GitHub Actions) and promotion
globs: .github/workflows/**, ci-cd/**, Makefile
---

# CI/CD

- `Makefile` is the single entry point; pipelines call `make` targets instead of reimplementing commands, so local and CI behave the same.
- GitHub Actions (`.github/workflows/`) is the only maintained provider. GitLab CI, CircleCI and Jenkins configurations are parked in `ci-cd/future/` and do not run; do not update them alongside GitHub changes. Reactivating one follows `ci-cd/future/README.md`.
- Test and lint steps must fail the pipeline. Do not add `|| true`, `continue-on-error` or soft-fail options to them (HIGH-013, fixed).
- Security gates fail the pipeline too: Trivy blocks fixable CRITICAL/HIGH dependency vulnerabilities and CRITICAL/HIGH Kubernetes/Terraform misconfigurations in `ci.yml`, and every image is scanned before it is pushed to ECR (`publish-ecr.yml`). Fix the finding; an exception goes in `.trivyignore.yaml` scoped to the exact paths with a `statement` explaining why it is acceptable.
- Pin actions and images to a version tag or SHA. Set minimal `permissions:` on GitHub workflows.
- Use OIDC to assume AWS roles from CI; never long-lived AWS keys in CI variables.
- Jobs that hit real AWS (`make test`, `apply`) must be opt-in (manual `workflow_dispatch` input or protected branch) and never run on pull requests from forks.
- Cache dependencies (Poetry, Terraform providers) keyed on lock files.
- Promotion (`environment-promotion.yml`, `gitops/scripts/promotion/`) updates Git (image tags / overlays) and lets ArgoCD reconcile; pipelines do not `kubectl apply` directly.
- Build images once, tag with git SHA, promote the same digest across environments.
