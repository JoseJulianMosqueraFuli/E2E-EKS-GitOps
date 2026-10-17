# AGENTS.md

Guide for AI agents (and human collaborators) working on this repository.

This is the shared entry point for agent instructions. `CLAUDE.md` imports this file with
`@AGENTS.md` and must remain a single-line import. Maintain shared instructions here and in
`.agents/rules/` so every agent follows the same guidance.
Kiro reads this file directly. Copilot's `.github/copilot-instructions.md` links here.

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
| `gitops/applications/projects/` | ArgoCD AppProjects + ApplicationSet |
| `gitops/charts/` | Helm charts (mlflow, kserve, kubeflow-pipelines, monitoring-stack) |
| `gitops/infrastructure/` | Flux-managed cluster infra (addons, controllers, networking, security) |
| `gitops/platform/` | AWS account/region for the overlays (`aws.env` is gitignored; `aws.env.example` is committed) |
| `gitops/scripts/` & `gitops/tests/` | GitOps automation + Hypothesis property tests |
| `ml-platform/src/` | Python ML code (models, data, pipelines, cli, monitoring, features) |
| `ml-platform/tests/` | Unit + integration tests (pytest) |
| `ml-platform/feature_repo/` | Feast feature repo (local backend) |
| `ml-platform/Dockerfile`, `Dockerfile.mlflow-server` | `mlops-platform` image (pipeline steps) and MLflow server image |
| `ci-cd/providers/jenkins/` | Jenkinsfile |
| `scripts/` | Top-level automation (`setup-mlops-stack.sh`, `bootstrap-terraform-backend.sh`) |
| `scripts/e2e/` | kind smoke test (CI only) |
| `.github/workflows/` | `ci.yml`, `ml-platform-image.yml`, `e2e-kind.yml`, `environment-promotion.yml` |
| `docs/` | Project documentation (`docs/README.md` is the hub) |
| `docs/architecture/` | Platform architecture and implementation overview |
| `docs/project/` | Canonical backlog and CRITICAL/HIGH findings |
| `docs/reports/` | Historical validation reports |
| `docs/proposals/` | Proposed future work |

## Canonical sources of truth

- **Backlog & priorities**: `docs/project/backlog.md` (canonical), `docs/project/critical.md` (CRITICAL/HIGH details).
- **Architecture overview**: [`docs/architecture/implementation.md`](docs/architecture/implementation.md).
- **Historical validation report**: [`docs/reports/validation-report.md`](docs/reports/validation-report.md) is a snapshot; current status belongs in the backlog.
- **Resilience and recovery proposal**: [`docs/proposals/resilience-recovery.md`](docs/proposals/resilience-recovery.md).
- **GitOps manifests**: `gitops/applications/apps/<app>/base/` is canonical. `k8s/mlops-stack/<app>/kustomization.yaml` should point to it (ref-bound, not duplicated; argo-workflows and mlflow point to the `dev` overlay so the AWS placeholders are resolved).
- **Documentation hub**: `docs/README.md`.
- **Image tags**: pin to semantic versions or SHAs. Gatekeeper enforces no `:latest` in production namespaces.

## Documentation placement

Keep only `README.md`, `README.es.md`, `SECURITY.md`, `AGENTS.md`, and `CLAUDE.md` at the repository root.
Place architecture, project tracking, reports, and proposals in their corresponding `docs/` directories
and register them in `docs/README.md`. Component-specific documentation stays next to its code.
When moving a document, update its links and references, including this file and `.agents/rules/`.

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

# Python ML platform (uses Poetry). Extras: validation, monitoring, features; dev = all + tooling
cd ml-platform && poetry install -E dev
poetry run python -m src.cli create-sample data/sample.csv --n-samples 1000
poetry run python -m src.cli train data/sample.csv
poetry run python -m src.cli step --help   # split / train / evaluate / register (what Argo runs)
poetry run pytest tests/ -v

# AWS account/region for the GitOps overlays
make platform-config                     # creates gitops/platform/aws.env from the example
make validate-platform-config            # fails if AWS_ACCOUNT_ID/AWS_REGION placeholders are unresolved

# GitOps Python tooling & tests (uses Poetry)
cd gitops && poetry install --with test,dev
poetry run pytest tests/ -v

# End-to-end smoke test: runs only in GitHub Actions (.github/workflows/e2e-kind.yml),
# which builds the images, creates kind and runs scripts/e2e/kind-smoke.sh. Not meant for local machines.

# Validation (lint/format/typecheck/k8s/tf)
make validate-all
make validate-python                     # flake8 + black --check + isort --check
make dev-lint                            # + mypy
make dev-format                          # black + isort (writes)
```

## Agent rules (always apply)

Before any change, read the shared [engineering](.agents/rules/engineering.md),
[architecture](.agents/rules/architecture.md), [security](.agents/rules/security.md), and
[ML architecture](.agents/rules/ml-architecture.md) rules. Then consult the
[rule index](.agents/README.md#rules) and read the rules matching the files and domains involved.
These references replace per-tool rule files. MCP servers are read-only by policy.

## Conventions

- **Python**: `black` (line-length 100), `isort` (profile=black), `flake8`, `mypy`. pytest config in `pyproject.toml`.
- **Terraform**: `terraform fmt -recursive`. Backend is **local** by default; see `infra/environments/*/main.tf` for the S3 backend activation checklist (requires AWS account).
- **Kubernetes**: prefer `kustomize build ... | kubectl --dry-run=client apply -f -` for validation.
- **Commits**: follow the existing conventional-commits style (e.g., `feat(chaos):`, `docs(readme):`, `fix(...)`). Keep messages concise.
- **Comments**: do NOT add comments unless explicitly requested.
- **Do not commit secrets**. `.secrets.baseline` + `detect-secrets` pre-commit hook are enforced.

## Sensitive areas — be careful

- **CI `|| true`**: test/lint steps in `.github/workflows/ci.yml`, `.gitlab-ci.yml`, `.circleci/config.yml` intentionally tolerate failures. **Do not remove `|| true` without explicit request** (tracked as HIGH-013 in `docs/project/critical.md`, owner: DevOps).
- **Terraform state**: backend blocks are commented out by design. Uncomment only after running `scripts/bootstrap-terraform-backend.sh` (needs AWS account).
- **Argo Workflows** (`k8s/mlops-stack/argo-workflows/`): already hardened (TLS + `--auth-mode=client` + emissary executor; SSO pending an OIDC provider). Don't reintroduce `docker.sock` mounts or `containerRuntimeExecutor: docker`.
- **Gatekeeper**: `no-latest-tag` constraint is active for production namespaces. Pin image tags.
- **AWS account / region**: never write them literally in manifests or docs. Use the `AWS_ACCOUNT_ID` / `AWS_REGION` placeholders and resolve them with Kustomize `replacements` from `gitops/platform/` (see its README). `gitops/platform/aws.env` is gitignored.
- **Images**: pipeline steps run on the single `mlops-platform` image (`ml-platform/Dockerfile`); add a `step` subcommand instead of a new image. CI builds only `linux/amd64` (EKS nodes are x86).
- **AWS costs**: `make test` and `make apply` hit real AWS. Prefer `test-terraform-plan` for CI/local validation.

## Known open work (see `docs/project/critical.md` / `docs/project/backlog.md`)

- CRIT-004: ArgoCD `mlops-core` AppProject is permissive (`sourceRepos: "*"`, `destinations: namespace: "*"`) — restrict.
- HIGH-006 / HIGH-007: `:latest` in the Evidently image and in the non-training Argo templates (training template already pinned).
- HIGH-001: Terraform S3 backend activation (account available; run `scripts/bootstrap-terraform-backend.sh <env> us-east-1`).
- HIGH-013: CI hides failures (intentional, do not touch unless asked).
- Before the first AWS deployment (`docs/project/backlog.md`): ArgoCD injection of `aws.env` (#48), IRSA roles for Argo/MLflow (#50), globally unique S3 bucket names (#51), images still missing in templates (#52), ECR publishing via OIDC (#55), first green `e2e-kind.yml` run (#56).
- Many MEDIUM/LOW items in `docs/project/backlog.md` (Istio mTLS gaps, Gatekeeper coverage, Helm chart hardening, ML platform debt).

## When adding a new MLOps app

1. Create base manifests under `gitops/applications/apps/<app>/base/`.
2. Add per-env overlays under `gitops/applications/apps/<app>/overlays/{dev,staging,prod}/`.
3. Register the app in the ApplicationSet (`gitops/applications/projects/mlops-applicationset.yaml`).
4. If the app has an ArgoCD AppProject, restrict `sourceRepos`, `destinations`, and resource whitelists (don't repeat CRIT-004).
5. Add the app to `Makefile` `validate-kubernetes` target's `kustomize build` list.
6. If it needs the AWS account or region, use the placeholders + `replacements` (see `gitops/platform/README.md`) and add the app to `validate-platform-config`.
7. Update `docs/project/backlog.md` / `docs/project/critical.md` if security-relevant.

## Misc env files

- `.pre-commit-config.yaml` — pre-commit hooks (detect-secrets, etc.). Run `make dev-setup` once.
- `.secrets.baseline` — baseline for detect-secrets.
- `Makefile` — single entry point for most operations.
- `.agents/` — source of truth for AI agent rules (`rules/`) and MCP servers (`mcp/servers.json`). See `.agents/README.md`.
- `CLAUDE.md`, `.github/copilot-instructions.md`, `.kiro/settings/mcp.json`, `.vscode/mcp.json`, `.mcp.json` — **generated** by `make agents-sync`; do not edit by hand. Shared rules stay in `.agents/`; per-tool rule copies are not generated.

*Last updated: 2026-10-17*
