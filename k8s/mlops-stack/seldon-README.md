# Seldon Core

> **DEPRECATED as manual manifests**
>
> The static YAML manifest that lived here has been removed because Seldon Core
> releases frequently and the manifest drifted from upstream CRDs.
>
> **Current source of truth:**
> `gitops/charts/kserve/` — KServe Helm chart (the officially recommended
> successor to Seldon Core for model serving on Kubernetes).
>
> If you still need Seldon Core specifically, use the official Helm chart:
> ```bash
> helm repo add seldon https://storage.googleapis.com/seldon-charts
> helm repo update
> helm upgrade --install seldon-core seldon/seldon-core-operator \
>   --namespace seldon-system --create-namespace
> ```
>
> For ArgoCD / GitOps deployment, see:
> `gitops/applications/projects/mlops-helm-repository.yaml`
