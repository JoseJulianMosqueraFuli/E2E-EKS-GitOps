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
| `argo-workflows` | Training step images (ECR `mlops-<env>-trainer`), `ecr-repository` parameter of the deployment and pipeline templates, `AWS_DEFAULT_REGION` env in every template |
| `mlflow` | Server image (ECR `mlops-<env>-mlflow-server`), IRSA role ARNs, SecretStore region, backup CronJob region, S3 endpoint in production |

Other apps (kserve, monitoring, kubeflow, external-secrets) still carry literal values or `ACCOUNT_ID`
placeholders and will be migrated to this mechanism (see `backlog.md`). Flux-managed infrastructure uses its
own per-cluster `cluster-config` ConfigMap with `postBuild.substitute`.

## Where the real values come from

- **Local / CI**: `aws.env` (CI creates it from the example; the kind E2E works with dummy values because its
  images are loaded locally under the dummy ECR names).
- **ArgoCD on AWS**: ArgoCD renders from git, so `aws.env` must be provided at render time. Pending decision
  (tracked in `backlog.md`): inject the values from the cluster registration (ApplicationSet cluster
  generator annotations → `kustomize.patches` on `platform-config`) or a Config Management Plugin.
