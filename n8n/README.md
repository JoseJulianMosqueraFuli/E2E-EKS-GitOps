# n8n workflow automation and deployment

## Purpose

n8n is intended for event-driven integration and operational automation across
the MLOps platform: connecting webhooks and external services, coordinating
notifications and human approvals, and initiating platform actions. It
complements rather than replaces Argo Workflows, which remains responsible for
the ML training and deployment pipelines.

## CI workflow tests

Run the tests locally with `make test-n8n`. GitHub Actions, GitLab CI, CircleCI,
and Jenkins use this same Makefile target and shared test script. Each
workflow's import and execution gets a 5-minute wall-clock limit by default;
adjust it with
`N8N_WORKFLOW_TIMEOUT=<duration>`. The test job is also bounded by a 30-minute
provider-level timeout. n8n also enforces a 4-minute execution timeout; the
remaining minute covers startup and shutdown. The runner needs GNU `timeout`,
`jq`, `make`, and access
to a Docker daemon. GitLab's Docker-in-Docker runner must allow privileged
services; CircleCI uses remote Docker, and Jenkins agents must provide Docker.
CircleCI and Jenkins compare changed files to `main` before running the tests.
In Jenkins, set `RUN_N8N_TESTS` to force a run if that comparison is unavailable
or no n8n-related files changed.

The standalone [GitHub Actions workflow](../.github/workflows/n8n.yml) runs when
files under `n8n/`, `Makefile`, or that workflow change, and can also be started
manually.
It executes the JSON workflows in `n8n/workflows/` in a temporary,
network-isolated n8n container pinned to version 2.42.6 and its image digest.
Each workflow is imported into a fresh instance and executed with the CLI. CI
publishes a Markdown summary and uploads the report and failure logs as an
artifact. Successful per-workflow logs are deleted before artifact collection;
only failure logs are retained.

The container runs with `--network none` so test workflows cannot call external
services; mock or avoid integrations in CI rather than weakening network
isolation. Its root filesystem is read-only, with the n8n data directory and
`/tmp` mounted as disposable tmpfs. The workflow JSON is streamed over Docker's
attached stdin into `/tmp`, which works with remote Docker daemons without a
host bind mount. All Linux capabilities are dropped and
privilege escalation is disabled. Memory, CPU, process count, and workflow
runtime are bounded to keep a test from consuming unbounded runner resources.

Add exported workflow JSON files to `n8n/workflows/` to include them in CI.
Keep workflow IDs, but do not commit credentials or production data. Workflows
must be safe to execute in an isolated test environment.

## Planned EKS deployment

n8n is not deployed to EKS by this CI job. Its later deployment will use
ArgoCD/GitOps manifests under
`gitops/applications/apps/n8n/`, with a canonical `base/` and environment
overlays at `overlays/dev/`, `overlays/staging/`, and
`overlays/production/`. The app will be registered with the existing GitOps
application configuration and promoted through environment overlays; CI will
not apply manifests directly to a cluster.

AWS account and region references must use the `AWS_ACCOUNT_ID` and
`AWS_REGION` placeholders supplied through `gitops/platform/` (see
[`gitops/platform/README.md`](../gitops/platform/README.md) and
[`gitops/platform/aws.env.example`](../gitops/platform/aws.env.example)).
The example values are placeholders only; never commit real account values or
credentials. Production deployment must source n8n credentials and its
encryption key from the existing secrets-management integration, not Git.
