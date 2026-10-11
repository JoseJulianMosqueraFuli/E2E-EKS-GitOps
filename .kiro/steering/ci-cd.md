---
inclusion: fileMatch
fileMatchPattern: [".github/workflows/**", ".gitlab-ci.yml", ".circleci/**", "ci-cd/**", "Makefile"]
---

# CI/CD

- `Makefile` is the single entry point; pipelines call `make` targets instead of reimplementing commands, so local and CI behave the same.
- Four providers are maintained (`.github/workflows/`, `.gitlab-ci.yml`, `.circleci/config.yml`, `ci-cd/providers/jenkins/Jenkinsfile`). A change in one usually needs the equivalent change in the others, or an explicit note why not.
- `|| true` on test/lint steps is intentional (HIGH-013). Do not remove it unless explicitly asked.
- Pin actions/orbs/images to a version tag or SHA. Set minimal `permissions:` on GitHub workflows.
- Use OIDC to assume AWS roles from CI; never long-lived AWS keys in CI variables.
- Jobs that hit real AWS (`make test`, `apply`) must be opt-in (manual `workflow_dispatch` input or protected branch) and never run on pull requests from forks.
- Cache dependencies (Poetry, Terraform providers) keyed on lock files.
- Promotion (`environment-promotion.yml`, `gitops/scripts/promotion/`) updates Git (image tags / overlays) and lets ArgoCD reconcile; pipelines do not `kubectl apply` directly.
- Build images once, tag with git SHA, promote the same digest across environments.
