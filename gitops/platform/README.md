# Platform configuration (AWS account and region)

Single place for the AWS values used by the GitOps overlays. Manifests never contain the account ID or the
region literally; they use the placeholders `AWS_ACCOUNT_ID` and `AWS_REGION`, which each overlay resolves
from this configuration with Kustomize `replacements`.

## Files

| File | In git | Purpose |
|------|--------|---------|
| `aws.env.example` | yes | Template with dummy values (`000000000000`, `us-east-1`) |
| `aws.env` | no (`.gitignore`) | Real values for your account |
| `kustomization.yaml` | yes | Generates the `platform-config` ConfigMap from `aws.env` (marked `local-config`, never deployed) |

```bash
make platform-config            # creates aws.env from the example if missing
$EDITOR gitops/platform/aws.env # set AWS_ACCOUNT_ID and AWS_REGION
make validate-platform-config   # fails if any placeholder is left unresolved
```

## What gets resolved

| App | Fields |
|-----|--------|
| `argo-workflows` | Pipeline images, inference repository, AWS region, IRSA role and environment/account/region-specific data buckets |
| `mlflow` | Server/backup images, separate IRSA roles, SecretStore region, backup bucket and production artifact bucket |
| `chaos` | MLflow canary images in dev/staging |
| `monitoring` | Service and drift-job images; other AWS integrations remain tracked in #49 |

Other apps (kserve, monitoring, kubeflow, external-secrets) still carry literal values or `ACCOUNT_ID`
placeholders and will be migrated to this mechanism (see `docs/project/backlog.md`). Flux-managed infrastructure reads a required `platform-runtime-config` ConfigMap through `substituteFrom`;
`flux.env.example` lists all values and `flux_runtime_config` is the Terraform output for cloud identifiers.

## Where the real values come from

- **Local / CI**: `aws.env` (CI creates it from the example; the kind E2E works with dummy values because its
  images are loaded locally under the dummy ECR names).
- **ArgoCD on AWS**: the `platform-kustomize` sidecar reads `argocd/platform-aws-config`, writes the ignored env file in its temporary checkout and runs Kustomize. The installer validates and creates this ConfigMap before waiting for the repo server. ApplicationSet selects the plugin explicitly. Missing/dummy values fail rendering.

See the [runtime configuration and recovery contract](../../docs/architecture/platform-runtime-config.md)
for bootstrap ordering, IAM roles, ECR publishing, state setup and restore commands. Production uses IRSA
for MLflow artifacts; it no longer injects the development gateway's static credentials into MLflow.
