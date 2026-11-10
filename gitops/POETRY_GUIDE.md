# GitOps Python dependencies

Run these commands from `gitops/`. Python requirements and dependency groups are declared in
[pyproject.toml](pyproject.toml); [poetry.lock](poetry.lock) pins the resolved versions.
This directory uses `package-mode = false` and does not install a Python application package.

## Installation

| Purpose | Command |
|---|---|
| Development and tests | `poetry install --with test,dev` |
| Tests only | `poetry install --only main,test` |
| Runtime tooling only | `poetry install --only main` |
| Documentation tools only | `poetry install --only main,docs` |

Groups: `main` contains Kubernetes clients and utilities; `test` contains pytest and Hypothesis;
`dev` contains linting and typing tools; `docs` contains MkDocs. Groups are not marked optional,
so plain `poetry install` includes all of them.

## Validation and updates

```bash
poetry check --lock
poetry run pytest tests/ -m "not integration" -q
poetry show --outdated
```

To update a selected dependency, use `poetry update <package>` and review both dependency files.
After editing constraints, run `poetry lock` and the relevant checks. Commit the lock alongside
`pyproject.toml` so CI and local installations resolve the same versions.

See the [test guide](tests/README.md) for cluster-dependent checks and the
[GitOps overview](README.md) for repository navigation.
