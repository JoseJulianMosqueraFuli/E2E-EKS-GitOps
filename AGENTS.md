# AGENTS.md

Guide for AI agents (and human collaborators) working on this repository.

## Project overview

End-to-end MLOps platform on Amazon EKS: Terraform infra → EKS cluster → GitOps (ArgoCD + Flux) → MLflow / Kubeflow / KServe / Monitoring. The ML platform code lives in `ml-platform/`.

## Repository layout

| Path | Purpose |
|------|---------|
| `infra/modules/` | Reusable Terraform modules (vpc, eks, s3, ecr, glue) |
| `infra/environments/{dev,staging,prod}/` | Per-environment Terraform roots |
| `k8s/mlops-stack/` | Operational K8s overlays (MLflow, KServe, monitoring, argo-workflows, feast) |
| `k8s/security/` | Istio mTLS, Gatekeeper/OPA policies |
| `gitops/applications/apps/<app>/base/` | **GitOps source of truth** — ArgoCD apps (base + overlays) |
| `gitops/applications/environments/` | Per-env application overlays |
| `gitops/applications/projects/` | ArgoCD AppProjects + ApplicationSet |
| `gitops/charts/` | Helm charts (mlflow, kserve, kubeflow-pipelines, monitoring-stack) |
| `gitops/infrastructure/` | Flux-managed cluster infra (addons, controllers, networking, security) |
| `gitops/scripts/` & `gitops/tests/` | GitOps automation + Hypothesis property tests |
| `ml-platform/src/` | Python ML code (models, data, pipelines, cli, monitoring, features) |
| `ml-platform/tests/` | Unit + integration tests (pytest) |
| `ml-platform/feature_repo/` | Feast feature repo (local backend) |
| `ci-cd/providers/jenkins/` | Jenkinsfile |
| `scripts/` | Top-level automation (`setup-mlops-stack.sh`, `bootstrap-terraform-backend.sh`) |
| `docs/` | Project documentation (`docs/README.md` is the hub) |

## Canonical sources of truth

- **Backlog & priorities**: `backlog.md` (canonical), `critical.md` (CRITICAL/HIGH details).
- **GitOps manifests**: `gitops/applications/apps/<app>/base/` is canonical. `k8s/mlops-stack/<app>/kustomization.yaml` should point to it (ref-bound, not duplicated).
- **Documentation hub**: `docs/README.md`.
- **Image tags**: pin to semantic versions or SHAs. Gatekeeper enforces no `:latest` in production namespaces.

## Common commands

```bash
# Infra
make init ENV=dev && make plan ENV=dev && make apply ENV=dev
make test-terraform-plan ENV=dev          # no AWS creds needed
make test                                 # Terratest (needs AWS, costs $$)

# MLOps stack
make mlops-core ENV=dev                   # MLflow + Monitoring
make mlops-full ENV=dev                   # + Kubeflow + KServe
make mlops-status

# Python ML platform (uses Poetry)
cd ml-platform && poetry install -E dev
poetry run python -m src.cli create-sample data/sample.csv --n-samples 1000
poetry run python -m src.cli train data/sample.csv
poetry run pytest tests/ -v

# GitOps Python tooling & tests (uses Poetry)
cd gitops && poetry install --with test,dev
poetry run pytest tests/ -v

# Validation (lint/format/typecheck/k8s/tf)
make validate-all
make validate-python                     # flake8 + black --check + isort --check
make dev-lint                            # + mypy
make dev-format                          # black + isort (writes)
```

## Conventions

- **Python**: `black` (line-length 100), `isort` (profile=black), `flake8`, `mypy`. pytest config in `pyproject.toml`.
- **Terraform**: `terraform fmt -recursive`. Backend is **local** by default; see `infra/environments/*/main.tf` for the S3 backend activation checklist (requires AWS account).
- **Kubernetes**: prefer `kustomize build ... | kubectl --dry-run=client apply -f -` for validation.
- **Commits**: follow the existing conventional-commits style (e.g., `feat(chaos):`, `docs(readme):`, `fix(...)`). Keep messages concise.
- **Comments**: do NOT add comments unless explicitly requested.
- **Do not commit secrets**. `.secrets.baseline` + `detect-secrets` pre-commit hook are enforced.

## Sensitive areas — be careful

- **CI `|| true`**: test/lint steps in `.github/workflows/ci.yml`, `.gitlab-ci.yml`, `.circleci/config.yml` intentionally tolerate failures. **Do not remove `|| true` without explicit request** (tracked as HIGH-013 in `critical.md`, owner: DevOps).
- **Terraform state**: backend blocks are commented out by design. Uncomment only after running `scripts/bootstrap-terraform-backend.sh` (needs AWS account).
- **Argo Workflows** (`k8s/mlops-stack/argo-workflows/`): already hardened (TLS + SSO + emissary executor). Don't reintroduce `docker.sock` mounts or `containerRuntimeExecutor: docker`.
- **Gatekeeper**: `no-latest-tag` constraint is active for production namespaces. Pin image tags.
- **AWS costs**: `make test` and `make apply` hit real AWS. Prefer `test-terraform-plan` for CI/local validation.

## Known open work (see `critical.md` / `backlog.md`)

- CRIT-004: ArgoCD `mlops-core` AppProject is permissive (`sourceRepos: "*"`, `destinations: namespace: "*"`) — restrict.
- HIGH-006 / HIGH-007: pin `:latest` in Evidently image and Argo workflow templates.
- HIGH-001: Terraform S3 backend activation (blocked on AWS account).
- HIGH-013: CI hides failures (intentional, do not touch unless asked).
- Many MEDIUM/LOW items in `backlog.md` (Istio mTLS gaps, Gatekeeper coverage, Helm chart hardening, ML platform debt).

## When adding a new MLOps app

1. Create base manifests under `gitops/applications/apps/<app>/base/`.
2. Add per-env overlays under `gitops/applications/apps/<app>/overlays/{dev,staging,prod}/`.
3. Register the app in `gitops/applications/environments/` and the ApplicationSet (`gitops/applications/projects/mlops-applicationset.yaml`).
4. If the app has an ArgoCD AppProject, restrict `sourceRepos`, `destinations`, and resource whitelists (don't repeat CRIT-004).
5. Add the app to `Makefile` `validate-kubernetes` target's `kustomize build` list.
6. Update `backlog.md` / `critical.md` if security-relevant.

## Misc env files

- `.pre-commit-config.yaml` — pre-commit hooks (detect-secrets, etc.). Run `make dev-setup` once.
- `.secrets.baseline` — baseline for detect-secrets.
- `Makefile` — single entry point for most operations.
- `.agents/` and `.kiro/` — existing AI agent task/spec scratch directories.

*Last updated: July 2026*