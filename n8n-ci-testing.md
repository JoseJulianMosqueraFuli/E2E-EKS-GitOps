# n8n workflow CI tests

GitHub Actions tests the workflows stored in `n8n/workflows/` using a temporary
container. Each JSON workflow is imported into a fresh n8n instance and executed
with the CLI; no n8n service or workflow data is persisted. The workflow job
publishes a Markdown summary and uploads `n8n-test-report.md` and failure logs
as an artifact.

Add exported workflow JSON files to `n8n/workflows/` to include them in CI. Keep
workflow IDs in the exported files, and do not include credentials or production
data. Workflows run during CI, so only add workflows that are safe to execute in
an isolated test environment.

The initial `ci-smoke-test.json` validates the n8n import-and-execute path. This
CI setup is a test-only first phase; it does not deploy n8n to EKS. EKS deployment
will be managed separately through GitOps.
