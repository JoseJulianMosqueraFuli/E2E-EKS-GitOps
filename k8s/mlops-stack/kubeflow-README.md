# Kubeflow Pipelines

> **DEPRECATED as manual manifests**
>
> The raw Kustomize manifests that lived here have been removed because they
> become stale quickly and are hard to maintain.
>
> **Current source of truth:**
> `gitops/charts/kubeflow-pipelines/` — Helm chart based on the official
> Kubeflow Pipelines distribution.
>
> Install via Helm:
> ```bash
> helm upgrade --install kubeflow-pipelines \
>   gitops/charts/kubeflow-pipelines/ \
>   --namespace kubeflow --create-namespace
> ```
>
> For ArgoCD / GitOps deployment, see:
> `gitops/applications/projects/mlops-helm-repository.yaml`
