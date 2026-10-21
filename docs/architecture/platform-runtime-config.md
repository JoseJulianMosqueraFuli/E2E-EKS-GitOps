# Platform configuration and recovery contract

[Documentation index](../README.md) · [Current backlog](../project/backlog.md)

## Decision (2026-10-20)

Terraform owns AWS resources; Flux owns cluster infrastructure; ArgoCD owns applications. An ignored
`gitops/platform/aws.env` cannot be read from an ordinary ArgoCD checkout. Committing account values
would duplicate configuration, and patching a generated ConfigMap would still require its missing env file.
The selected solution is the `platform-kustomize` Config Management Plugin, with a separate temporary
volume and the same pinned ArgoCD image as the repository server.

The installer creates `argocd/platform-aws-config` from a validated local `aws.env`. The plugin injects
that configuration into its temporary checkout and runs Kustomize. It rejects missing or dummy account
values. ApplicationSet selects the plugin explicitly. Local and kind checks continue to use the example
configuration. One ArgoCD installation currently supplies one AWS account and region to its applications;
separate accounts/regions need a scoped configuration extension before being registered there.

This follows the [ArgoCD sidecar plugin model](https://argo-cd.readthedocs.io/en/release-2.9/operator-manual/config-management-plugins/).

## AWS resources

- Data and backup bucket names include the environment, account and region. Outputs are the integration
  contract. Changing names on an existing deployment may replace buckets: review the real Terraform
  plan and migrate data before applying it.
- `workload-identity` creates separate roles for MLflow artifacts, Argo steps, PostgreSQL backups and
  MLflow secret retrieval. Trust policies match an exact namespace, service account and STS audience.
  ECR push permissions for Argo are limited to its inference repository. `ecr:GetAuthorizationToken`
  uses `Resource: "*"` because that API does not support repository resource scoping.
- `ecr-publisher` trusts only the configured repository and GitHub environment. Dev can create the
  account-wide GitHub OIDC provider; set `github_oidc_provider_arn` when one already exists.
- `.github/workflows/publish-ecr.yml` is manual and publishes the initial **dev** images with semantic
  and commit tags. Configure `AWS_ROLE_ARN` and `AWS_REGION` in the protected GitHub `dev` environment.
  Run it with the platform version used by the overlays. Promotion of the same digest into staging/prod
  repositories is tracked separately; rebuilding an image is not promotion.

None of these resources are created by validation. Secrets Manager database/gateway values must also
exist before External Secrets can populate the Kubernetes Secrets.

## Bootstrap sequence

After the cloud configuration is reviewed and applied by the operator:

1. Use Terraform `platform_config` output to populate `gitops/platform/aws.env`.
2. Run `gitops/scripts/install-gitops-controllers.sh install` with the intended `KUBE_CONTEXT`.
   It installs the complete pinned Flux distribution and waits for ArgoCD's application controller as a
   StatefulSet. ArgoCD requires real platform values before its repository server starts.
3. Copy `gitops/platform/flux.env.example` to the ignored `gitops/platform/flux.env`. Merge the Terraform
   `flux_runtime_config` output and review capacity defaults. No `REPLACE_` value may remain.
4. Run `FLUX_CONFIG_FILE=gitops/platform/flux.env ENVIRONMENT=dev gitops/scripts/install-gitops-controllers.sh reconcile`.
   Flux reads `platform-runtime-config` for addons, networking and security. Each resource tree has one
   owner; child Flux Kustomizations reconcile actual `gitops/infrastructure/...` paths.
5. Register the environment cluster in ArgoCD, publish dev images and verify application health before
   starting a fault.

The Terraform roots declare an unconfigured S3 backend. Local checks use `init -backend=false`.
`scripts/bootstrap-terraform-backend.sh <env> "$AWS_REGION"` creates an account/region-specific state
bucket and lock table and writes the ignored `infra/environments/<env>/backend.hcl`. It configures
versioning, SSE-KMS, public-access blocking and a TLS-only policy. It does not initialize Terraform or
migrate state. Review the file, then initialize explicitly; use `-migrate-state` only after reviewing an
existing-state migration. HIGH-001 stays open until that operational step succeeds.

## Backup and recovery

The server image and locked client both use MLflow 3.17.1. Before upgrading an existing database,
take and verify a backup, then run `mlflow db upgrade` with the existing backend URI during a planned
maintenance window. No live database migration is performed by these repository changes. Follow the
[MLflow migration guide](https://mlflow.org/docs/latest/self-hosting/migration/).

New experiments use the MLflow artifact proxy. Existing experiments retain their stored artifact
locations; review their client access and migration separately. The server permits the rendered internal
Service names and localhost. Add any intended ingress hostname explicitly to
`MLFLOW_SERVER_ALLOWED_HOSTS` before exposing it; do not disable the security middleware.

The CronJob uses `mlops-platform` with PostgreSQL 15 client tools and boto3. The rendered host is the
actual `<env>-mlflow-postgresql` Service. The job runs without root, drops capabilities and uses a temporary
writable volume. Dumps have unique keys and SHA-256 metadata; restore verifies the downloaded content.

```bash
make backup-mlflow ENV=dev
make restore-mlflow ENV=dev BACKUP_KEY=mlflow-backups/<dump>.dump RESTORE_DATABASE=recovery_check
```

Create an empty recovery database first. Restore refuses the source database, connection-string targets,
nonempty databases and corrupt backups. It never switches the running MLflow backend automatically.
The custom backup prefix must remain inside the IAM-permitted `mlflow-backups/` path.

## Verification boundary

GitHub Actions kind tests validate data, train/register, enforce the promotion gate, restore PostgreSQL,
install Flux/Litmus, run pod deletion and stop a second workflow using Argo `Stop`. They retain logs,
workflows and Litmus results for 14 days. `Terminate` and a failed Argo controller can bypass exit handlers;
the runbook's manual recovery procedure still applies. Kind tests run only in GitHub Actions.
The job pins kind 0.30.0 and the Kubernetes 1.34.0 node digest from the
[official kind release](https://github.com/kubernetes-sigs/kind/releases/tag/v0.30.0), satisfying the Flux
controller and stable admission-policy API requirements.

Local checks cover manifests, policy configuration and failure behavior with doubles. A temporary
MLflow 3.17.1 HTTP server with SQLite and local artifact storage also passed the Chaos canary round trip
and allowed/denied hostname checks. Dependency installation from the corrected lock passed its
compatibility check. These checks do not prove
CNI enforcement, IAM access, EBS recovery, GPU rescheduling or EKS availability. The zone preflight rejects
PVC-backed target workloads and insufficient aggregate CPU/memory/GPU capacity; it does not solve
stateful HA or prove per-pod affinity/taint feasibility. PostgreSQL and the dev/staging artifact gateway
still need a cross-zone recovery strategy.
