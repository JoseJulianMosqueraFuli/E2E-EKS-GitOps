# Platform Architecture Principles

## Layering

The platform is built in strict layers. Each layer only depends on the ones below it and is owned by one tool:

| Layer | Tool | Location |
|-------|------|----------|
| Cloud foundation (VPC, EKS, S3, ECR, Glue, KMS, IAM) | Terraform | `infra/` |
| Cluster infrastructure (controllers, addons, networking, security) | Flux | `gitops/infrastructure/` |
| Platform & ML applications (MLflow, KServe, Kubeflow, Feast, monitoring) | ArgoCD | `gitops/applications/` |
| ML code (training, features, monitoring jobs) | Python / Poetry | `ml-platform/` |

- Never manage the same resource from two layers (e.g. a namespace created by both Terraform and ArgoCD, or IAM roles in both Terraform and manifests).
- Cross-layer contracts go through outputs: Terraform outputs (role ARNs, bucket names, cluster endpoint) are consumed by GitOps via values/overlays or External Secrets, not hard-coded.
- Git is the single source of truth for cluster state. Manual `kubectl` changes are drift and must be reverted or codified.

## Environments

- `dev`, `staging`, `prod` share the same modules/bases; they differ only through variables (Terraform) and overlays (Kustomize/Helm values).
- Promotion flows dev → staging → prod (`.github/workflows/environment-promotion.yml`, `gitops/scripts/promotion/`). Never introduce prod-only code paths that were not exercised in staging.
- Prod defaults: multi-AZ, autoscaling, PodDisruptionBudgets, pinned images, Gatekeeper enforcement, mTLS STRICT.

## AWS Well-Architected checklist

Apply the six pillars to every design decision:

- **Operational excellence**: everything as code, observable (metrics, logs, traces), runbooks in `docs/`.
- **Security**: least privilege (IRSA per workload), encryption at rest (KMS) and in transit (TLS/mTLS), private subnets for nodes, no public S3.
- **Reliability**: multi-AZ, health probes, PDBs, retries with backoff, backups (MLflow DB/artifacts), tested restore.
- **Performance efficiency**: right-size requests/limits, use GPU node pools only for GPU workloads, autoscaling (HPA / Karpenter / cluster-autoscaler, KServe autoscaling).
- **Cost optimization**: tag everything (`Environment`, `Project`, `ManagedBy`), Spot for stateless/training workloads, scale-to-zero for dev inference, S3 lifecycle policies. See `docs/cost-estimation.md`.
- **Sustainability**: avoid idle capacity, prefer Graviton where images support arm64.

## Design decisions

- Non-trivial architectural changes need a short decision record: context, options considered, decision, consequences. Put it in `docs/` and link it from `docs/README.md`.
- Prefer managed AWS services when they remove undifferentiated operational load (RDS for MLflow backend, S3 for artifacts) unless cost or portability is an explicit requirement.
- Prefer boring, well-supported technology. A new controller or operator must justify its operational cost.
- Keep diagrams (`docs/architecture.drawio`, `docs/diagrams/`) in sync with the real topology.
