# Contributing

[← Documentation index](README.md)

Start with the [backlog](project/backlog.md) and the [architecture overview](architecture/implementation.md).
The shared [engineering conventions](../AGENTS.md) describe repository boundaries and sensitive areas.

## Submit a change

1. Fork the repository and create a branch for one change.
2. Update the relevant code and its guide. Keep the English and Spanish READMEs aligned if you change the public overview.
3. Open a pull request describing the problem, the change, and how you verified it.
4. Review the applicable GitHub Actions results and address failures. Include reproduction steps and relevant logs when reporting a bug.

Use conventional commit messages, such as `docs(readme): simplify project overview` or
`fix(terraform): correct module input`.
Report vulnerabilities through [SECURITY.md](../SECURITY.md).

## Validate through GitHub Actions

A local Kubernetes cluster is not required to contribute.

| Change | Validation |
|---|---|
| Terraform | [CI Pipeline](../.github/workflows/ci.yml) checks formatting and validates dev, staging, and prod without AWS credentials. |
| Initial AWS plan | [Terraform CI guide](terraform-ci.md) explains OIDC setup and the manual plan workflow. |
| Kubernetes, Helm, or Python | [CI Pipeline](../.github/workflows/ci.yml) runs the corresponding checks. |
| ML platform image | [Image workflow](../.github/workflows/ml-platform-image.yml) tests the image and publishes to GHCR on non-PR runs. |
| Training integration | [E2E workflow](../.github/workflows/e2e-kind.yml) builds the images and runs the training flow on a temporary kind cluster. |
| Documentation | Check relative links, command accuracy, and English/Spanish consistency. |

Image and E2E workflows have path filters; see their definitions for triggers. Repository maintainers
can also start the E2E workflow manually from **Actions → E2E (kind) → Run workflow**.
Initial plans use empty state and do not deploy resources. AWS deployment and Terratest are separate
operations: `make apply`, `make destroy`, and `make test` access real AWS resources.

## Optional local development

Use the guide for the component you are changing:

- [ML platform setup](../ml-platform/README.md) and [ML development guide](ml-platform-guide.md).
- [GitOps Python setup](../gitops/POETRY_GUIDE.md) and [test suite](../gitops/tests/README.md).
- [Makefile](../Makefile) for formatting and validation targets.

Python uses Black, isort, flake8, and mypy. Terraform uses `terraform fmt`.
Dependency versions live in each component's `pyproject.toml`, lockfiles, and Terraform declarations.
Keep credentials, state files, and local AWS configuration out of Git.

## Documentation changes

Keep the root READMEs short. Put detailed instructions in the relevant guide, link new documents from
the [documentation index](README.md), and update relative links when moving files.
Track current work in the [backlog](project/backlog.md); historical reports remain snapshots.
