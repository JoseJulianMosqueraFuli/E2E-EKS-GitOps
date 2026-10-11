---
inclusion: always
---

# Engineering Working Agreements

These rules apply to every task, in every part of the repository. Read `AGENTS.md` for layout and commands.

## Before changing anything

- Identify the canonical source before editing: `gitops/applications/apps/<app>/base/` for manifests, `backlog.md` / `critical.md` for priorities, `docs/README.md` for docs.
- Check `critical.md` and `backlog.md` for an existing item (CRIT-xxx, HIGH-xxx) that covers the change and reference it.
- Prefer the smallest change that solves the problem. Do not refactor unrelated code in the same change.
- Never edit generated or vendored content (`build/`, `*.egg-info`, `mlruns/`, `.hypothesis/`, `.terraform/`, files generated from `.agents/`).

## While changing

- Match surrounding style, naming and idioms. Do not add comments unless asked.
- Keep environments symmetric: a change in `dev` must have an explicit decision for `staging` and `prod` (apply, defer with a backlog item, or document why not).
- Pin versions everywhere: container images (semver or digest, never `:latest`), Helm charts, Terraform providers/modules, GitHub Actions, Python dependencies (via `poetry.lock`).
- Never commit secrets, tokens, kubeconfigs, `*.tfvars` or state files. `detect-secrets` runs in pre-commit; update `.secrets.baseline` only for verified false positives.

## Verifying

- Run the narrowest validation that covers the change, then report the real outcome:
  - Terraform: `terraform fmt -recursive` + `make validate-terraform ENV=<env>` / `make test-terraform-plan ENV=<env>`
  - Kubernetes: `kustomize build <path> | kubectl apply --dry-run=client -f -`, `make validate-kubernetes`
  - Python: `make validate-python`, `make dev-lint`, `poetry run pytest tests/ -v` in `ml-platform/` or `gitops/`
- Never run `make apply`, `make test`, `make destroy`, `kubectl apply` (non dry-run) or anything that touches real AWS without explicit request: it costs money and mutates shared state.
- Do not remove `|| true` from CI steps (HIGH-013) unless explicitly asked.

## Delivering

- Conventional commits: `feat(scope):`, `fix(scope):`, `docs(scope):`, `chore(scope):`, `refactor(scope):`. Concise subject, imperative mood.
- Update `backlog.md` / `critical.md` when a change closes or creates a security-relevant or tracked item.
- Update docs when behavior, commands or architecture change (see the documentation rule).
