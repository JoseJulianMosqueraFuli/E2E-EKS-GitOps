---
description: Python code style, typing, packaging and testing for ml-platform and gitops tooling
globs: **/*.py, **/pyproject.toml
---

# Python

## Tooling

- Two Poetry projects: `ml-platform/` and `gitops/`. Add dependencies with `poetry add` (dev tools in the dev group/extras) and commit `poetry.lock`.
- Format: `black` (line-length 100) + `isort` (profile black). Lint: `flake8`. Types: `mypy`.
- Commands: `make dev-format`, `make validate-python`, `make dev-lint`.

## Code

- Type hints on all public functions and methods; avoid `Any` unless at an I/O boundary.
- Small, pure functions for transformations; isolate I/O (S3, MLflow, Kubernetes, HTTP) behind thin clients so logic is testable without network.
- Configuration via typed settings (dataclasses/pydantic) loaded from env vars or files, not module-level globals or hard-coded paths/URIs.
- Use `logging` (structured where possible), never `print` in library code. Do not log secrets or raw records with personal data.
- Raise specific exceptions with context; do not swallow exceptions with bare `except:`.
- Keep the CLI (`src/cli.py`) thin: parse args, call library code.

## Tests

- `pytest` under `tests/` mirroring `src/` structure; unit tests must not need AWS, a cluster or network.
- Use fixtures and small synthetic datasets; set seeds for anything random.
- Property-based tests with Hypothesis for parsers/validators (pattern used in `gitops/tests/`).
- Mark slow/integration tests and keep them out of the default fast path.
- Every bug fix adds a test that fails without the fix.
