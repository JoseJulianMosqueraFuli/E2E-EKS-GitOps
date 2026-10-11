---
description: Security baseline for infrastructure, Kubernetes, ML and supply chain
globs:
---

# Security Baseline

See `SECURITY.md`, `docs/security-best-practices.md` and open items in `critical.md`.

## Identity and access

- Least privilege everywhere. Each workload gets its own IRSA role scoped to the exact resources it needs (specific bucket ARNs/prefixes, specific ECR repos). No `*` actions or resources unless AWS requires it, and justify it when it does.
- Kubernetes RBAC: namespace-scoped Roles over ClusterRoles; no `cluster-admin` bindings for workloads.
- ArgoCD AppProjects must restrict `sourceRepos`, `destinations` and resource whitelists (do not repeat CRIT-004).

## Secrets

- Never in Git, images, Terraform variables with defaults, ConfigMaps or Helm values.
- Use AWS Secrets Manager / SSM + External Secrets Operator (`gitops/applications/apps/external-secrets/`).
- Reference credentials via environment variables in local tooling (`${GITHUB_PERSONAL_ACCESS_TOKEN}`), never inline.

## Workload hardening

- Pods: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true` where possible, drop all capabilities, `seccompProfile: RuntimeDefault`.
- No `hostPath`, `hostNetwork`, `privileged`, or `docker.sock` mounts (Argo Workflows uses the emissary executor; keep it).
- Every namespace: default-deny NetworkPolicy plus explicit allows; Istio mTLS STRICT in staging/prod.
- Gatekeeper constraints (`k8s/security/gatekeeper/`) are guardrails, not suggestions. New policies start in `dryrun`/`warn` then move to `deny`.

## Data and encryption

- S3: block public access, SSE-KMS, versioning on artifact/state buckets, TLS-only bucket policy.
- EKS: secrets envelope encryption with KMS, private endpoint for prod, control-plane logging enabled.
- ML data: treat training data and model artifacts as sensitive. No PII in logs, metrics labels or MLflow params.

## Supply chain

- Pin images by semver or digest; ECR scan-on-push enabled; prefer minimal/distroless base images.
- Pin GitHub Actions to a version tag or SHA, Terraform providers with `~>`, Python deps via `poetry.lock`.
- Only pull charts/images from trusted registries declared in `gitops/infrastructure/sources/`.
- When adding a dependency, check maintenance status and known CVEs first.
