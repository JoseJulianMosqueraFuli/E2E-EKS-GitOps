# Backlog Completo - E2E-EKS-GitOps

**Mapa canónico de TODO el trabajo pendiente.**  
Para detalles técnicos de issues CRÍTICOS y ALTOS, ver: [`critical.md`](critical.md)  
Para items de producto y roadmap, ver: [`docs/PENDING.md`](docs/PENDING.md)

---

## Dashboard de Estado

| Area | CRITICAL | HIGH | MEDIUM | LOW | Total |
|------|----------|------|--------|-----|-------|
| Seguridad | 1 | 3 | 9 | 2 | 15 |
| Infra (Terraform) | 0 | 4 | 6 | 2 | 12 |
| GitOps / K8s | 0 | 3 | 8 | 3 | 14 |
| Plataforma ML (Python) | 0 | 2 | 6 | 2 | 10 |
| Monitoreo | 0 | 2 | 4 | 2 | 8 |
| CI/CD | 0 | 1 | 5 | 2 | 8 |
| Arquitectura / Extras | 0 | 0 | 0 | 7 | 7 |
| **TOTAL** | **1** | **15** | **38** | **20** | **74** |

---

## CRITICAL (4) — Ver `critical.md`

| ID | Issue | Archivo(s) | Owner | Estado |
|----|-------|------------|-------|--------|
| CRIT-001 | Argo Workflows sin TLS | `k8s/mlops-stack/argo-workflows/server-deployment.yaml` | Platform | ✅ Corregido 2026-06-07 |
| CRIT-002 | Argo Workflows auth basica | `k8s/mlops-stack/argo-workflows/server-deployment.yaml` | Security | ✅ Corregido 2026-06-07 |
| CRIT-003 | Docker executor obsoleto + docker.sock | `argo-workflows/configmap.yaml`, `workflow-templates/*` | DevSecOps | ✅ Corregido 2026-06-07 |
| CRIT-004 | AppProject ArgoCD permisivo | `gitops/applications/projects/mlops-core.yaml` | GitOps | ⏳ Pendiente |

---

## HIGH (15)

### Seguridad / Infra (8)

| ID | Issue | Archivo(s) | Fix |
|----|-------|------------|-----|
| HIGH-001 | Backend local Terraform | `infra/environments/*/main.tf` | Descomentar S3+DynamoDB |
| HIGH-002 | Kubernetes 1.28 near EOL | `infra/modules/eks/variables.tf` | Actualizar a 1.30/1.31 |
| HIGH-003 | Node egress sin restriccion | `infra/modules/vpc/variables.tf` | Restringir `node_egress_cidrs` |
| HIGH-004 | CIDR hardcoded en prod | `infra/environments/prod/main.tf` | Parametrizar |
| HIGH-005 | Feast `latest` tag | `k8s/mlops-stack/feast/feast-server.yaml` | Pinear version |
| HIGH-006 | Evidently `latest` tag | `gitops/charts/monitoring-stack/values.yaml` | Pinear version |
| HIGH-007 | Workflow templates `latest` tags | `argo-workflows/workflow-templates/*.yaml` | Pinear version |
| HIGH-008 | KServe HTTP sin HTTPS redirect | `k8s/mlops-stack/kserve/istio-config.yaml` | Forzar HTTPS |

### Plataforma / Monitoreo (5)

| ID | Issue | Archivo(s) | Fix |
|----|-------|------------|-----|
| HIGH-009 | Grafana `emptyDir` | `gitops/applications/apps/monitoring/base/grafana-deployment.yaml` | Cambiar a PVC |
| HIGH-010 | Prometheus Deployment | `gitops/applications/apps/monitoring/base/prometheus-deployment.yaml` | Cambiar a StatefulSet |
| HIGH-011 | Errores de import Python | `ml-platform/src/main.py` | Corregir imports |
| HIGH-012 | `fastapi`/`uvicorn` faltantes | `ml-platform/pyproject.toml` | Agregar deps |
| HIGH-013 | CI oculta fallas | `.github/workflows/ci.yml`, `.gitlab-ci.yml`, `.circleci/config.yml` | Eliminar `|| true` |

---

## MEDIUM (38)

### Istio / Service Mesh (5)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 1 | Falta STRICT mTLS en `models`, `ml-monitoring`, `external-secrets`, `knative-serving` | `k8s/security/istio/peer-authentications.yaml` |
| 2 | Falta default-deny en `argo-workflows`, `feast`, `kubeflow`, `models` | `k8s/security/istio/authorization-policies.yaml` |
| 3 | Falta allow health-checks en todos los namespaces | `k8s/security/istio/authorization-policies.yaml` |
| 4 | Falta allow Prometheus scrape en todos los namespaces monitoreados | `k8s/security/istio/authorization-policies.yaml` |
| 5 | Falta allow `argo-workflows` -> MLflow y `kubeflow` -> KServe | `k8s/security/istio/authorization-policies.yaml` |
| 6 | DestinationRule catch-all muy amplio (`*.svc.cluster.local`) | `k8s/security/istio/destination-rules.yaml` |

### Gatekeeper / OPA (3)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 7 | No cubre namespaces: `feast`, `models`, `ml-monitoring`, `external-secrets`, `knative-serving` | `k8s/security/gatekeeper/constraints/*.yaml` |
| 8 | PodSecurity template no verifica initContainers, runAsUser, seccompProfile a nivel pod | `k8s/security/gatekeeper/templates/pod-security.yaml` |
| 9 | IngressHosts permite `*.example.com` | `k8s/security/gatekeeper/constraints/ingress-hosts.yaml` |

### GitOps / ArgoCD (6)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 10 | `monitoring` en `k8s/` no apunta a `gitops/applications/apps/monitoring/` | `k8s/mlops-stack/monitoring/kustomization.yaml` |
| 11 | `argo-workflows` en `k8s/` no apunta a gitops | `k8s/mlops-stack/argo-workflows/kustomization.yaml` |
| 12 | `feast` en `k8s/` no apunta a gitops | `k8s/mlops-stack/feast/kustomization.yaml` |
| 13 | No existen Applications para: feast, argo-workflows, external-secrets, gatekeeper, istio | `gitops/applications/environments/` |
| 14 | ApplicationSet no genera apps para `argo-workflows`, `feast`, `external-secrets` | `gitops/applications/projects/mlops-applicationset.yaml` |
| 15 | Duplicacion de alertas Prometheus | `k8s/mlops-stack/monitoring/prometheus-alerts.yaml` vs `gitops/applications/apps/monitoring/base/alertmanager-config.yaml` |
| 16 | Desincronizacion de versiones: Prometheus `v2.45.0` vs `v2.48.0` | `k8s/` vs `gitops/` |
| 17 | Desincronizacion de versiones: Grafana `10.0.3` vs `10.2.2` | `k8s/` vs `gitops/` |

### Helm Charts (4)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 18 | MLflow chart usa `python:3.11-slim` en vez de imagen MLflow oficial | `gitops/charts/mlflow/values.yaml` |
| 19 | KServe chart: `urlScheme: "http"` | `gitops/charts/kserve/values.yaml` |
| 20 | KServe chart deshabilita NetworkPolicy y PDB | `gitops/charts/kserve/values.yaml` |
| 21 | Kubeflow chart usa Argo workflow controller `v3.3.10` (antiguo) | `gitops/charts/kubeflow-pipelines/Chart.yaml` |

### Terraform Infra (6)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 22 | KMS en dev sin `enable_key_rotation` | `infra/environments/dev/main.tf` |
| 23 | EKS addon `vpc_cni` sin IRSA | `infra/modules/eks/main.tf` |
| 24 | `allowed_principals` vacio por defecto en modulo ECR | `infra/modules/ecr/variables.tf` |
| 25 | `node_group_desired_size` sin validacion vs min/max | `infra/modules/eks/variables.tf` |
| 26 | Glue table schema hardcodeado | `infra/environments/*/main.tf` |
| 27 | Glue crawlers schedule hardcodeado en los 3 ambientes | `infra/environments/*/main.tf` |

### Python / ML Platform (7)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 28 | `prometheus-client` inconsistente: pyproject <0.17 vs Dockerfile 0.17.1 | `ml-platform/pyproject.toml`, `Dockerfile.monitoring` |
| 29 | `LabelEncoder` incompatible con `ColumnTransformer` | `ml-platform/src/data/feature_engineering.py` |
| 30 | Duplicacion de clase `ModelMonitor` | `src/utils/monitoring.py`, `src/monitoring/model_monitor.py` |
| 31 | Transformers custom definidos pero nunca usados | `ml-platform/src/data/feature_engineering.py` |
| 32 | `dvc`, `awscli`, `kubernetes` en deps sin uso evidente | `ml-platform/pyproject.toml` |
| 33 | `awscli` como dependencia de libreria (deberia ser dev/extra) | `ml-platform/pyproject.toml` |
| 34 | Feast feature repo: falta backend productivo (Redis/DynamoDB) y deployment server K8s | `ml-platform/feature_repo/`, `k8s/mlops-stack/feast/` |

### Monitoreo (4)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 35 | ConfigMap `evidently-config` referencia key `s3_bucket` inexistente | `k8s/mlops-stack/monitoring/drift-cronjob.yaml` |
| 36 | Retencion Prometheus muy corta (200h ~ 8.3 dias) | `k8s/mlops-stack/monitoring/prometheus-stack.yaml` |
| 37 | Prometheus `web.enable-admin-api` habilitado | `gitops/charts/monitoring-stack/values.yaml` |
| 38 | Evidently image `latest` en monitoring chart | `gitops/charts/monitoring-stack/values.yaml` |

### CI/CD (5)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 39 | GitLab CI usa `bitnami/kubectl:latest` | `.gitlab-ci.yml` |
| 40 | CircleCI usa `bitnami/kubectl:latest` | `.circleci/config.yml` |
| 41 | GitHub Actions: pytest/flake8/black con `|| true` | `.github/workflows/ci.yml` |
| 42 | GitLab CI: pytest/flake8/black con `|| true` | `.gitlab-ci.yml` |
| 43 | CircleCI: pytest/flake8/black con `|| true` | `.circleci/config.yml` |
| 44 | Falta pipeline automatizada para Terratest Go | `.github/workflows/ci.yml` |

---

## LOW (20)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 1 | Argo Workflows: `readOnlyRootFilesystem: false` en server | `argo-workflows/server-deployment.yaml` |
| 2 | Argo Workflows: falta NetworkPolicy para namespace | `k8s/mlops-stack/argo-workflows/` |
| 3 | Argo Workflows: falta PDB para server y controller | `k8s/mlops-stack/argo-workflows/` |
| 4 | Feast: sin `securityContext` en containers | `k8s/mlops-stack/feast/feast-server.yaml` |
| 5 | Feast: Redis sin `securityContext` | `k8s/mlops-stack/feast/redis.yaml` |
| 6 | Feast: Redis sin autenticacion | `k8s/mlops-stack/feast/redis.yaml` |
| 7 | Feast: falta HPA | `k8s/mlops-stack/feast/` |
| 8 | Feast: falta PDB | `k8s/mlops-stack/feast/` |
| 9 | Feast: falta ServiceMonitor | `k8s/mlops-stack/feast/` |
| 10 | MLflow: falta VPA | `k8s/mlops-stack/mlflow/` |
| 11 | KServe: falta VPA | `k8s/mlops-stack/kserve/` |
| 12 | KServe examples: `custom-nlp-server:latest` y `feature-transformer:latest` | `k8s/mlops-stack/kserve/examples/` |
| 13 | MLflow chart: `readOnlyRootFilesystem: false` | `gitops/charts/mlflow/values.yaml` |
| 14 | Pre-commit hooks: versiones antiguas | `.pre-commit-config.yaml` |
| 15 | AWS Account ID placeholder `123456789012` en workflow | `argo-workflows/workflow-templates/model-deployment-template.yaml` |
| 16 | Nombres de buckets S3 hardcodeados en manifests | Varios en `k8s/` |
| 17 | `__main__` en `training_pipeline.py` ejecuta ejemplo con side effects | `ml-platform/src/pipelines/training_pipeline.py` |
| 18 | `import numpy as np` redundante en `feature_store_client.py` | `ml-platform/src/features/feature_store_client.py` |
| 19 | `roc_auc_score` calculado con etiquetas duras (incorrecto) | `ml-platform/src/models/classification_model.py` |
| 20 | `validate_config` no incluye `"ridge"` ni `"lasso"` | `ml-platform/src/utils/config_manager.py` |

---

## Arquitectura / Extras (7) — Product Roadmap

| # | Item | Descripcion | Complejidad |
|---|------|-------------|-------------|
| 1 | End-to-end test AWS | Terraform -> EKS -> ArgoCD -> MLflow -> KServe | Alta |
| 2 | Feature Store real | Feast con backend Redis/DynamoDB + integracion pipelines | Media |
| 3 | Kubecost / OpenCost | Exportador real de costos, reemplazar dashboard estimado | Media |
| 4 | Certificado ACM | TLS real para Ingress de MLflow/KServe/Grafana | Baja |
| 5 | Model Governance | Approval workflows con OPA/Gatekeeper + gates en ArgoCD | Alta |
| 6 | Multi-cluster | ArgoCD ApplicationSet con cluster generator | Media |
| 7 | Teams Notifications | Integracion Microsoft Teams ademas de Slack | Baja |
| 8 | ArgoCD Image Updater | Bumps automaticos de imagenes desde ECR/GHCR | Media |
| 9 | Ampliar tests integracion | Coverage de `ml-platform/tests/` | Media |
| 10 | Troubleshooting guide | Basado en experiencia real de deploy | Baja |
| 11 | Actualizar pre-commit hooks | detect-secrets, terraform_fmt, etc. | Baja |
| 12 | Actualizar versiones EKS addons | Fijar versiones de EBS CSI, VPC CNI, etc. | Baja |

---

## Estrategia de Remediacion (Sugerida)

### Wave 1: Seguridad Critica (~4h)
- CRIT-001, CRIT-002, CRIT-003, CRIT-004

### Wave 2: Robustecimiento (~6h)
- HIGH-005 a HIGH-013 (imagenes, Python, CI)

### Wave 3: Infraestructura (~4h)
- HIGH-001 a HIGH-004, MEDIUM Terraform items

### Wave 4: GitOps Completo (~8h)
- MEDIUM GitOps, Istio, Gatekeeper, Helm charts

### Wave 5: Validacion (~requiere AWS)
- e2e test, Terratest, ACM

### Wave 6: Producto (~semanas)
- Feast real, Kubecost, Model Governance, Multi-cluster

---

*Ultima actualizacion: 2026-06-06*  
*Fuentes: `critical.md`, `docs/PENDING.md`, revision manual de 120+ archivos*
