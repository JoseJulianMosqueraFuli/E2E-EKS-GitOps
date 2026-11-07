# Inactive CI providers (future work)

[← Documentation index](../../docs/README.md)

GitHub Actions (`.github/workflows/`) is the only maintained and validated CI/CD platform.
The GitLab CI, CircleCI, and Jenkins configurations are kept here as references for future work.
None of them runs: GitLab and CircleCI only read their configuration from the repository root,
and no Jenkins job points to this path.

## Decision record (2026-11-07)

- **Context:** four providers were declared as maintained, but only GitHub Actions has run history:
  CI Pipeline, ML Platform Image, and the kind E2E test (training, backup/restore, and Chaos).
  The other three have no recorded runs for this repository and had drifted from the GitHub workflows.
- **Decision:** keep only GitHub Actions active. Move the other configurations here without changes.
- **Consequences:** changes to CI only need to be applied to `.github/workflows/`. The files here are not
  kept in sync, so treat them as stale until revalidated. Slack notifications remain available through
  ArgoCD Notifications, Alertmanager, and the Python notifier; the Jenkins `slackSend` step does not run.

## Contents

| Path | Original location | What it did |
|---|---|---|
| `gitlab/.gitlab-ci.yml` | `.gitlab-ci.yml` | Terraform, Kubernetes, and Helm validation; ML tests and lint; Checkov |
| `circleci/config.yml` | `.circleci/config.yml` | Terraform and Helm validation, ML tests, security scan |
| `jenkins/Jenkinsfile` | `ci-cd/providers/jenkins/Jenkinsfile` | Parameterized Terraform tests, plan/apply, data validation, training, Slack |

## Known gaps before reactivating

- Images such as `bitnami/kubectl:latest`, `bridgecrew/checkov:latest`, `hashicorp/terraform:1.6`, and
  `cimg/go:1.21` are unpinned or outdated (backlog #39).
- Jenkins uses stored `aws-credentials` and `kubeconfig` credentials instead of OIDC, which the
  [CI/CD rule](../../.agents/rules/ci-cd.md) requires, and runs `terraform apply` directly after `plan`
  without an approval gate.
- None of them includes the image build or the kind E2E test from `.github/workflows/`.

## Reactivating a provider

1. Move the file back to its original location (see the table above), or point the Jenkins job to it.
2. Close the gaps above and align its jobs with `.github/workflows/ci.yml` through the `make` targets.
3. Run it and record the first passing run in [`docs/project/backlog.md`](../../docs/project/backlog.md).
4. List it again as maintained in [`AGENTS.md`](../../AGENTS.md) and the [CI/CD rule](../../.agents/rules/ci-cd.md).
