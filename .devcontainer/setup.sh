#!/usr/bin/env bash
# Provisions the Codespace / devcontainer: installs Python deps with Poetry for
# both projects, wires up pre-commit, and seeds the GitOps platform config.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "=== Poetry version ==="
poetry --version

# Keep virtualenvs inside each project so VS Code can discover the interpreter.
poetry config virtualenvs.in-project true

echo "=== Installing ml-platform (Poetry, dev extras) ==="
# The lock may be behind pyproject (e.g. new dev tools); refresh it if needed.
( cd ml-platform && poetry lock --no-update || poetry lock ) && ( cd ml-platform && poetry install -E dev )

echo "=== Installing gitops (Poetry, test + dev groups) ==="
( cd gitops && { poetry lock --no-update || poetry lock; } && poetry install --with test,dev )

echo "=== Installing pre-commit hooks ==="
# pre-commit lives in the ml-platform venv; run it from the repo root so it
# finds the .git dir and the root .pre-commit-config.yaml.
MLP_VENV="$(cd ml-platform && poetry env info --path)"
"${MLP_VENV}/bin/pre-commit" install --install-hooks

echo "=== Seeding GitOps platform config ==="
make platform-config

echo "=== Done. Activate an environment with: cd ml-platform && poetry shell ==="
