---
inclusion: fileMatch
fileMatchPattern: ["k8s/**", "gitops/applications/**", "gitops/charts/**", "gitops/infrastructure/**"]
---

# Kubernetes & GitOps

## Source of truth

- `gitops/applications/apps/<app>/base/` is canonical. Environment differences go in `overlays/{dev,staging,prod}/` as patches, never as copied manifests.
- `k8s/mlops-stack/<app>/` must reference the GitOps base (ref-bound), not duplicate it.
- Cluster infrastructure (controllers, addons, networking, security) is Flux-managed in `gitops/infrastructure/`; applications are ArgoCD-managed. Do not mix the two for the same resource.
- Adding an app: follow the checklist in `AGENTS.md` ("When adding a new MLOps app").

## Manifests

- Always set: resource `requests` and `limits` (memory limit = request for critical workloads), `readinessProbe` and `livenessProbe` (plus `startupProbe` for slow starters), `securityContext` per the security rule.
- Standard labels: `app.kubernetes.io/name`, `app.kubernetes.io/instance`, `app.kubernetes.io/version`, `app.kubernetes.io/component`, `app.kubernetes.io/part-of: mlops-platform`, `app.kubernetes.io/managed-by`.
- Images pinned by semver or digest. `:latest` is rejected by Gatekeeper in prod (HIGH-006, HIGH-007 still open).
- Prod: `replicas >= 2`, PodDisruptionBudget, topology spread across zones, HPA where load varies.
- One namespace per platform component; every namespace gets a default-deny NetworkPolicy and Istio sidecar injection label where mTLS is required.
- ServiceAccounts per workload with IRSA annotation; `automountServiceAccountToken: false` when the pod does not call the API.

## Helm charts (`gitops/charts/`)

- Bump `version` in `Chart.yaml` on every chart change; `appVersion` tracks the application.
- Secure defaults in `values.yaml` (non-root, resources set, no public ingress). Environments override only what differs.
- Validate with `helm lint` and `helm template ... | kubectl apply --dry-run=client -f -`.

## ArgoCD / Flux

- Applications use automated sync with `prune: true` and `selfHeal: true` only after the app is stable; use sync waves for ordering (CRDs → operators → instances).
- AppProjects restrict `sourceRepos`, `destinations` and cluster resource whitelists (CRIT-004).
- Reference a pinned `targetRevision` (tag/branch per environment), not `HEAD` in prod.
- Never fix drift with `kubectl edit`; change Git.

## Validation

```bash
kustomize build gitops/applications/apps/<app>/overlays/<env> | kubectl apply --dry-run=client -f -
make validate-kubernetes
cd gitops && poetry run pytest tests/ -v
```

Agents must not run mutating `kubectl`, `helm install/upgrade`, `argocd app sync` or `flux reconcile` against a real cluster unless explicitly asked.
