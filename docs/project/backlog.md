# Backlog Completo - E2E-EKS-GitOps

[← Documentation index](../README.md)

**Mapa canónico de TODO el trabajo pendiente y completado.**  
Para detalles técnicos de issues CRÍTICOS y ALTOS (CVSS, fix concreto), ver: [`docs/project/critical.md`](critical.md)

---

## Revision operativa — 2026-10-20

**Se corrigieron los bloqueos de implementacion de Chaos y varios contratos del despliegue. Falta ejecutar la nueva cobertura de CI y validar el entorno AWS real.** No se aplico Terraform ni se inyectaron fallos en EKS.

### Correcciones implementadas

- Bootstrap completo de Flux 2.7.5, APIs estables, rutas reales del repositorio y reconciliacion por capas sin doble propiedad. ArgoCD espera el application-controller como StatefulSet. El plugin `platform-kustomize` inyecta la configuracion fuera de Git y rechaza valores ficticios.
- Roles IRSA separados para Argo, MLflow, secretos de MLflow y backup. Buckets con sufijo de cuenta/region, backend bootstrap con nombre unico y publicacion inicial dev en ECR por OIDC. La activacion y el plan AWS siguen pendientes.
- Backup con cliente PostgreSQL/boto3, host correcto por overlay, ejecucion sin root, checksum y restore a una base vacia distinta. MLflow usa proxy de artefactos; en produccion usa IRSA y no las credenciales del gateway de desarrollo.
- Roles de Chaos separados, guardas de admision, canarios de datos/artefactos, predicciones con asercion y preflight AZ que bloquea PVCs y capacidad insuficiente. Los engines declaran `annotationCheck: "false"` para no depender de una anotacion ausente.
- GitHub Actions kind incluye validacion de datos, entrenamiento/gate, backup/restore, Flux/Litmus, pod-delete, cancelacion `Stop`, limpieza y evidencia retenida. Aun no se ha verificado un run verde de esta ampliacion.
- Eliminadas las imagenes inexistentes de validacion, deployment y notificacion del pipeline principal. Monitoring usa dependencias bloqueadas y una imagen versionada. El despliegue KServe requiere todavia prueba real.

### Evidencia local

- 417 pruebas GitOps aprobadas, incluidas las 32 de Chaos, el bootstrap del backend y la paridad de versiones cliente/servidor MLflow. Se excluyen las pruebas que requieren un cluster real.
- Suite ML: 166 aprobadas, una omitida y un xpass; 28 pruebas de backup, canarios y validacion del pipeline aprobadas tras las ultimas incorporaciones.
- 30 overlays autorizados por el AppProject; seis overlays Argo/MLflow sin placeholders; render del plugin desde un checkout sin `aws.env`; lint offline de Argo aprobado.
- Terraform dev/staging/prod validado sin backend ni llamadas de aprovisionamiento. `make test-terraform-plan` valida; no genera un plan real. Las pruebas de cluster siguen excluidas localmente.

### Orden de cierre operativo

| Prioridad | Pendiente | Evidencia necesaria |
|-----------|-----------|---------------------|
| P0 | Ejecutar la ampliacion de GitHub Actions (#54/#61/#62) | Charts reales reconciliados, backup restaurado, Litmus Pass y limpieza tras Stop |
| P0 | Configurar/aplicar AWS (#48/#50/#51/#55, HIGH-001) y completar contratos de otras apps (#49) | Plan revisado, backend activo, secretos disponibles, imagenes publicadas y ArgoCD saludable |
| P0 antes de fallos de zona | Recuperacion de almacenamiento y afinidades (#64) | Restore/HA entre zonas y capacidad de reubicacion demostrados; el preflight rechaza PVCs por defecto |
| P1 | Confirmar permisos, SLO/RTO/RPO y evidencia en EKS (#60/#63) | Permisos efectivos, predicciones/datos conservados, panel de resultados y tiempos medidos |
| P1 | Promocion del mismo digest ECR y ciclo completo (#65/#52/#53) | dev → staging → prod sin reconstruir; train → register → serve → monitor comprobado |
| P2 | Particion de red (#59), EC2 stop (#58), mTLS/Gatekeeper y Feast productivo (#34) | Aislamiento CNI, recuperacion y servicios de produccion verificados |

Detalles y comandos: [contrato de configuracion y recuperacion](../architecture/platform-runtime-config.md).

---

## Completado (historial)

- [x] Model Monitoring con Evidently - Detectar data drift y model drift automaticamente `(2026-05-16)`
- [x] Dashboards de Grafana pre-configurados - Para MLflow, KServe, y metricas de modelos `(2026-05-16)`
- [x] ArgoCD - GitOps real para deployment continuo `(2026-05-16)`
- [x] Slack Notifications - Hook en ArgoCD annotations + Python notifier + Jenkins slackSend + Alertmanager config + ArgoCD Notifications Controller desplegado `(2026-05-19)` - COMPLETO
- [x] Cost Monitoring - Dashboard de Grafana con costos estimados `(2026-05-16)` - Parcial: falta exportador real (Kubecost/OpenCost)
- [x] Auto-retraining Pipeline - Template de 7 pasos con DAG y logica condicional. Reemplazado con carga real de MLflow y Evidently `(2026-05-19)` - COMPLETO
- [x] CI/CD - GitHub Actions (CI + promotion) + Jenkins pipeline + promotion script con validacion `(2026-05-16)`
- [x] Hardening de staging/prod - Labels corregidos, KMS 30d/14d, ECR IMMUTABLE en prod, node egress restringido en prod, backend S3 comments corregidos `(2026-05-19)` - COMPLETO
- [x] A/B Testing Framework - WorkflowTemplate con experimentos, metricas estadisticas, auto-promotion `(2026-05-19)` - COMPLETO
- [x] PyProject.toml packaging - Corregido mlops_platform a cli:main, mypy target 3.10 `(2026-05-19)`
- [x] Documentacion sincronizada - READMEs, gitops/README, gitops/SETUP, IMPLEMENTATION_STATUS, VALIDATION_REPORT, quick-start y ml-platform guide alineados con el estado real del repo `(2026-05-20)`
- [x] Documentacion re-sincronizada - Diagramas de estructura actualizados `(2026-05-31)`
- [x] Reporte de auditoria completa - Revison de 120+ archivos, 6000+ lineas, hallazgos mapeados en `docs/project/critical.md` y `docs/project/backlog.md` `(2026-06-06)`
- [x] Feature Store con Feast (parcial) - Feature repo local: definiciones en feature_definitions.py, datos parquet (model_features, transaction_stats, user_profile), online_store.db, registry.db, tests unitarios. Falta: backend productivo (Redis/DynamoDB), server K8s `(2026-06-07)`
- [x] Codigo muerto eliminado - `ModelMonitor` duplicado, `CustomTransformers` sin uso, deps infladas (`dvc`, `awscli`, `kubernetes`) removidas `(2026-07-13)`
- [x] Egress de nodos restringido a VPC en dev/staging y parametrizado en prod `(2026-07-13)`
- [x] KServe Gateway con HTTPS redirect automatico `(2026-07-13)`
- [x] `LabelEncoder` incompatible reemplazado por `OrdinalEncoder` en `categorical_strategy='label'` `(2026-07-13)`
- [x] Argo Workflows v3.5.2 -> v4.0.13 (CRDs, RBAC, config, server) y Kubeflow Pipelines 2.0.x -> 2.17.2 (imagenes `ghcr.io/kubeflow`). Pendiente validar en cluster `(2026-10-10)`
- [x] Imagen unica `mlops-platform` (ml-platform/Dockerfile) + subcomandos `step split|train|evaluate|register`; plantilla de entrenamiento migrada; gate contra el modelo `@champion` `(2026-10-10)`
- [x] MLflow: imagen propia con psycopg2/boto3 (la oficial no los trae), init containers usaban hosts sin prefijo de entorno, NetworkPolicy con selectores inexistentes y sin puerto 9000 `(2026-10-10)`
- [x] Region migrada a us-east-1; imagenes mapeadas a ECR por overlay; cuenta/region desde `gitops/platform/aws.env` (fuera de git); bootstrap de backend compatible con us-east-1 `(2026-10-10)`
- [x] Smoke test E2E en kind (GitHub Actions): Argo + MLflow + entrenamiento + gate de promocion `(2026-10-10)` - primer verde registrado en `2ca2b2e` (2026-10-11), ver #56; no cubre Chaos
- [x] Terraform en GitHub Actions: validacion de dev/staging/prod y workflow manual de planes iniciales con OIDC de lectura, sin apply `(2026-10-17)` - implementado; pendiente configurar rol/variables AWS y verificar primer run. Ver `docs/terraform-ci.md`. HIGH-001 y #55 siguen pendientes.

- [x] Chaos revisado: barrera de inicio para la sonda, downtime por tiempo real, observacion hasta completar los engines, mutex, preflight de desalojo por zona y limpieza con errores visibles. RBAC de charts limitado (HIGH-014). `(2026-10-17)` - validacion estatica y pruebas con dobles; ejecucion EKS pendiente. EC2 stop #58, particion de red desactivada #59, separacion de roles #60.
---

## Dashboard de Estado

| Area | Estado verificable al 2026-10-20 |
|------|--------------------------------|
| CRITICAL historicos | 4 corregidos en codigo/manifiestos; permisos efectivos de CRIT-004 pendientes de comprobar en EKS |
| HIGH historicos | 11 corregidos en codigo; HIGH-001 y HIGH-013 abiertos; HIGH-014 mitigado en manifiestos |
| GitOps / Chaos | Bootstrap y E2E Chaos implementados; render/pruebas locales aprobados; ejecucion de CI/EKS pendiente |
| Proceso ML | Pipeline principal y monitoring corregidos; validar la ampliacion data → train → serve y publicacion |
| AWS / recuperacion | Validacion dev/staging/prod aprobada; plan real, despliegue, restore y resiliencia por zona pendientes |

Los estados por ID y la evidencia de la revision sustituyen los antiguos totales y puntuaciones estimadas, que mezclaban trabajo resuelto, duplicados y validacion funcional pendiente.

---

## CRITICAL (4) — Ver `docs/project/critical.md`

| ID | Issue | Archivo(s) | Owner | Estado |
|----|-------|------------|-------|--------|
| CRIT-001 | Argo Workflows sin TLS | `k8s/mlops-stack/argo-workflows/server-deployment.yaml` | Platform | ✅ Corregido 2026-06-07 |
| CRIT-002 | Argo Workflows auth basica | `k8s/mlops-stack/argo-workflows/server-deployment.yaml` | Security | ✅ Corregido 2026-06-07 |
| CRIT-003 | Docker executor obsoleto + docker.sock | `argo-workflows/configmap.yaml`, `workflow-templates/*` | DevSecOps | ✅ Corregido 2026-06-07 |
| CRIT-004 | AppProject ArgoCD permisivo | `gitops/applications/projects/mlops-core.yaml` | GitOps | ✅ Corregido en manifiestos; confirmado por render de 30 overlays el 2026-10-20. Verificacion efectiva EKS pendiente |

---

## HIGH (14)

### Seguridad / Infra (9)

| ID | Issue | Archivo(s) | Fix |
|----|-------|------------|-----|
| HIGH-001 | Backend local Terraform | `infra/environments/*/main.tf` | Seguir checklist de activacion en `main.tf` (requiere cuenta AWS) |
| HIGH-002 | Kubernetes 1.28 near EOL | `infra/modules/eks/variables.tf` | ✅ Actualizado a 1.32 (2026-06-09) |
| HIGH-003 | Node egress sin restriccion | `infra/environments/dev/main.tf`, `infra/environments/staging/main.tf` | ✅ Restringido a `var.vpc_cidr` (2026-07-13) |
| HIGH-004 | CIDR hardcoded en prod | `infra/environments/prod/main.tf` | ✅ Parametrizado con `var.vpc_cidr` + `var.node_egress_cidrs` (2026-07-13) |
| HIGH-005 | Feast `latest` tag | `k8s/mlops-stack/feast/feast-server.yaml` | ✅ Pineado a `0.40.1` en `gitops/applications/apps/feast/base/kustomization.yaml` (2026-06-26) |
| HIGH-006 | Imagenes de monitoring versionadas | `Dockerfile.monitoring`, `monitoring/base/` | Corregido en codigo; build/publicacion CI pendiente |
| HIGH-007 | Imagenes del pipeline principal versionadas | `argo-workflows/workflow-templates/*.yaml` | Corregido en codigo; serving E2E pendiente (#52) |
| HIGH-008 | KServe HTTP sin HTTPS redirect | `gitops/applications/apps/kserve/base/istio-config.yaml` | ✅ Agregado `tls.httpsRedirect: true` (2026-07-13) |
| HIGH-014 | Charts Litmus concedian acceso directo a secretos de todo el cluster | `gitops/applications/apps/chaos/base/litmus.yaml`, `rbac.yaml` | Corregido en manifiestos: eliminado administrador del catalogo; operador solo lee secretos de `litmus`. Verificar RBAC efectivo en EKS; roles de fallos aun amplios (#60). |

### Plataforma / Monitoreo (5)

| ID | Issue | Archivo(s) | Fix |
|----|-------|------------|-----|
| HIGH-009 | Grafana `emptyDir` | `gitops/applications/apps/monitoring/base/grafana-deployment.yaml` | ✅ Corregido 2026-06-08 |
| HIGH-010 | Prometheus Deployment | `gitops/applications/apps/monitoring/base/prometheus-deployment.yaml` | ✅ Corregido 2026-06-08 |
| HIGH-011 | Errores de import Python | `ml-platform/src/main.py` | ✅ Corregido 2026-06-08 |
| HIGH-012 | `fastapi`/`uvicorn` faltantes | `ml-platform/pyproject.toml` | ✅ Corregido 2026-06-08 |
| HIGH-013 | CI oculta fallas | `.github/workflows/ci.yml`, `.gitlab-ci.yml`, `.circleci/config.yml` | Eliminar `|| true` |

---

## MEDIUM — pendientes y resueltos

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

### GitOps / ArgoCD (8)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 45 | Argo `instanceID: argo-workflows` exige el label `workflows.argoproj.io/controller-instanceid` en cada Workflow; las WorkflowTemplates y KFP no lo ponen, por lo que el controller las ignora (confirmado en kind 2026-10-10) | `gitops/applications/apps/argo-workflows/base/configmap.yaml` | ✅ `instanceID` eliminado (un solo controller) 2026-10-10 |
| 46 | Archivo de workflows deshabilitado: requiere Postgres/MySQL (bloque `persistence` removido porque sin DB el controller no arranca) | `gitops/applications/apps/argo-workflows/base/configmap.yaml` |
| 48 | Plugin `platform-kustomize` implementado y probado desde checkout sin `aws.env`; configurar `platform-aws-config` y verificar render/sync real de ArgoCD. Una cuenta/region por instalacion | `gitops/applications/projects/mlops-applicationset.yaml`, `gitops/platform/` |
| 49 | Migrar kserve, monitoring, kubeflow y external-secrets al mecanismo `gitops/platform` (aun tienen region literal o placeholders `ACCOUNT_ID`) | `gitops/applications/apps/{kserve,monitoring,kubeflow,external-secrets}/` |
| 50 | Roles IRSA de Argo, MLflow, backup y lectura de secretos implementados en `workload-identity`; verificar trust, acceso S3/KMS/Secrets Manager y ECR tras aplicar Terraform | `infra/`, `gitops/applications/apps/argo-workflows/base/rbac.yaml` |
| 57 | MinIO dejo de publicar imagenes (Docker Hub y quay.io responden 401; repo archivado): reemplazado por Versity Gateway `versity/versitygw:v1.8.0` (S3 compatible, Apache-2). Quedan los nombres `mlflow-minio*` (Service, Secret, PVC) y menciones en docs/diagramas; renombrar a `mlflow-s3` y evaluar S3 real en dev | `gitops/applications/apps/mlflow/base/minio-*.yaml`, `docs/` |
| 58 | EC2 stop/termination sigue diferido: requiere catalogo `kube-aws`, una identidad exclusiva con alcance por tags y recuperacion demostrada. El rol de nodos actual solo modifica recursos Kubernetes | `infra/modules/eks/`, `gitops/applications/apps/chaos/base/` |
| 59 | Particion KServe→MLflow desactivada: `NAMESPACE_SELECTOR` era una allow list y las NetworkPolicies son aditivas; verificar enforcement del CNI, aislar un workload desechable y probar conectividad antes/durante/despues junto con disponibilidad de inferencia | `gitops/applications/apps/chaos/experiments/pod-network-partition-kserve-mlflow.yaml`, `infra/modules/eks/` |
| 60 | Roles separados por fallo/namespace y workflows MLflow/nodo; politicas de admision restringen seleccion de cuentas y pods del fallo de borrado. Validacion efectiva y abort/cleanup incluidos en kind CI; EKS y frontera del operador privilegiado pendientes | `gitops/applications/apps/chaos/base/`, `workflows/` |
| 61 | Bootstrap completo/versionado de Flux, APIs v1/v2, rutas corregidas y espera StatefulSet de ArgoCD implementados. Runtime config obligatorio y dependencias de capas corregidas. Falta instalacion/sync desde cluster vacio verificados | `gitops/scripts/install-gitops-controllers.sh`, `gitops/infrastructure/controllers/` |
| 64 | Preflight AZ bloquea workloads con PVC en la zona objetivo y falta de CPU/memoria/GPU fuera de ella. Sigue pendiente HA/restore entre zonas y viabilidad por afinidades; PostgreSQL/gateway siguen con una replica y gp3 | `gitops/applications/apps/mlflow/`, `gitops/applications/apps/chaos/workflows/az-failure-test.yaml` |
| 47 | argo-server usa `--auth-mode=sso` pero el ConfigMap no define bloque `sso` (issuer, clientId, clientSecret): el server entra en CrashLoopBackOff con `Error: issuer empty` (confirmado en kind 2026-10-10) | `gitops/applications/apps/argo-workflows/base/server-deployment.yaml` | ✅ Cambiado a `--auth-mode=client` (token de Kubernetes + RBAC) 2026-10-10. SSO/OIDC pendiente de proveedor |
| 10 | `monitoring` en `k8s/` no apunta a `gitops/applications/apps/monitoring/` | `k8s/mlops-stack/monitoring/kustomization.yaml` | ✅ Corregido 2026-06-26 |
| 11 | `argo-workflows` en `k8s/` no apunta a gitops | `k8s/mlops-stack/argo-workflows/kustomization.yaml` | ✅ Corregido 2026-06-26 |
| 12 | `feast` en `k8s/` no apunta a gitops | `k8s/mlops-stack/feast/kustomization.yaml` | ✅ Corregido 2026-06-26 |
| 13 | No existen Applications para: feast, argo-workflows, external-secrets, gatekeeper, istio | `gitops/applications/environments/` | ✅ Corregido 2026-06-26 |
| 14 | ApplicationSet no genera apps para `argo-workflows`, `feast`, `external-secrets` | `gitops/applications/projects/mlops-applicationset.yaml` | ✅ Corregido 2026-06-26 |
| 15 | Duplicacion de alertas Prometheus | `k8s/mlops-stack/monitoring/prometheus-alerts.yaml` vs `gitops/applications/apps/monitoring/base/alertmanager-config.yaml` | ✅ Corregido 2026-06-26 |
| 16 | Desincronizacion de versiones: Prometheus `v2.45.0` vs `v2.48.0` | `k8s/` vs `gitops/` | ✅ Corregido 2026-06-26 |
| 17 | Desincronizacion de versiones: Grafana `10.0.3` vs `10.2.2` | `k8s/` vs `gitops/` | ✅ Corregido 2026-06-26 |

### Helm Charts (4)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 18 | MLflow chart usa `python:3.11-slim` en vez de imagen MLflow oficial | `gitops/charts/mlflow/values.yaml` |
| 19 | KServe chart: `urlScheme: "http"` | `gitops/charts/kserve/values.yaml` |
| 20 | KServe chart deshabilita NetworkPolicy y PDB | `gitops/charts/kserve/values.yaml` |
| 21 | Kubeflow chart usa Argo workflow controller `v3.3.10` (antiguo) | `gitops/charts/kubeflow-pipelines/Chart.yaml` | ✅ Valor sin uso eliminado; Argo real actualizado a v4.0.13 y KFP a 2.17.2 (2026-10-10) |

### Terraform Infra (6)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 22 | KMS en dev sin `enable_key_rotation` | `infra/environments/dev/main.tf` |
| 23 | EKS addon `vpc_cni` sin IRSA | `infra/modules/eks/main.tf` |
| 24 | `allowed_principals` vacio por defecto en modulo ECR | `infra/modules/ecr/variables.tf` |
| 25 | `node_group_desired_size` sin validacion vs min/max | `infra/modules/eks/variables.tf` |
| 26 | Glue table schema hardcodeado | `infra/environments/*/main.tf` |
| 27 | Glue crawlers schedule hardcodeado en los 3 ambientes | `infra/environments/*/main.tf` |
| 51 | Nombres de buckets de datos, artefactos, backups y state incluyen cuenta/region. Revisar replacements/migracion en un plan real si existen buckets previos; otros contratos de apps siguen en #49 | `infra/`, `gitops/applications/apps/*`, `scripts/bootstrap-terraform-backend.sh` |

### Python / ML Platform (7)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 28 | `prometheus-client` inconsistente: pyproject <0.17 vs Dockerfile 0.17.1 | `ml-platform/pyproject.toml`, `Dockerfile.monitoring` |
| 29 | `LabelEncoder` incompatible con `ColumnTransformer` | `ml-platform/src/data/feature_engineering.py` | ✅ Corregido 2026-07-13 |
| 30 | Duplicacion de clase `ModelMonitor` | `src/utils/monitoring.py`, `src/monitoring/model_monitor.py` | ✅ Corregido 2026-07-13 |
| 31 | Transformers custom definidos pero nunca usados | `ml-platform/src/data/feature_engineering.py` | ✅ Corregido 2026-07-13 |
| 32 | `dvc`, `awscli`, `kubernetes` en deps sin uso evidente | `ml-platform/pyproject.toml` | ✅ Corregido 2026-07-13 |
| 33 | `awscli` como dependencia de libreria (deberia ser dev/extra) | `ml-platform/pyproject.toml` | ✅ Corregido 2026-07-13 |
| 34 | Feast feature repo: falta backend productivo (Redis/DynamoDB) y deployment server K8s | `ml-platform/feature_repo/`, `k8s/mlops-stack/feast/` |
| 52 | Pipeline principal migrado a `mlops-platform` (`validate-data`, `validate-deployment`, `notify`) y recurso KServe; corregido tag de inferencia para usar el repo existente. Pendiente E2E de serving y ejemplos `feature-transformer` de KServe | `gitops/applications/apps/argo-workflows/base/workflow-templates/` |
| 53 | Dockerfile.monitoring usa Poetry/lock y Evidently compatible; imagen del servicio/CronJob versionada y build en CI. Pendiente primer build publicado y servicio saludable | `ml-platform/Dockerfile.monitoring` |

### Monitoreo (4)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 35 | ConfigMap `evidently-config` referencia key `s3_bucket` inexistente | `k8s/mlops-stack/monitoring/drift-cronjob.yaml` |
| 36 | Retencion Prometheus muy corta (200h ~ 8.3 dias) | `k8s/mlops-stack/monitoring/prometheus-stack.yaml` |
| 37 | Prometheus `web.enable-admin-api` habilitado | `gitops/charts/monitoring-stack/values.yaml` |
| 38 | Evidently image `latest` en monitoring chart | `gitops/charts/monitoring-stack/values.yaml` |
| 54 | Backup/restore reparado: PostgreSQL client + boto3, host por overlay, IRSA/bucket, contexto restricted y checksum; restore bloquea origen/base ocupada. Pruebas locales aprobadas; ensayo real agregado al kind CI y pendiente en EKS | `gitops/applications/apps/mlflow/base/backup-cronjob.yaml` |
| 63 | Sondas funcionales implementadas: run persistente durante fallo, artefacto antes/despues y prediccion AZ con jq. Falta acordar SLO/RTO/RPO productivos, dashboard y medicion EKS; CI conserva resultados 14 dias | `gitops/applications/apps/chaos/workflows/`, `gitops/applications/apps/monitoring/` |

### CI/CD (5)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 39 | GitLab CI usa `bitnami/kubectl:latest` | `.gitlab-ci.yml` |
| 40 | CircleCI usa `bitnami/kubectl:latest` | `.circleci/config.yml` |
| 41 | GitHub Actions: pytest/flake8/black con `|| true` | `.github/workflows/ci.yml` |
| 42 | GitLab CI: pytest/flake8/black con `|| true` | `.gitlab-ci.yml` |
| 43 | CircleCI: pytest/flake8/black con `|| true` | `.circleci/config.yml` |
| 44 | Falta pipeline automatizada para Terratest Go | `.github/workflows/ci.yml` |
| 55 | Rol OIDC por entorno y publicacion inicial dev en `publish-ecr.yml` implementados. Configurar provider/variables del entorno GitHub, aplicar IAM y ejecutar; promocion sin reconstruir en #65 | `.github/workflows/ml-platform-image.yml`, `infra/` |
| 56 | Primer run verde de `e2e-kind.yml` (entrena, evalua, registra y bloquea por el gate de promocion) | `.github/workflows/e2e-kind.yml`, `scripts/e2e/kind-smoke.sh` | ✅ Verde en `2ca2b2e` (2026-10-11): Secrets sin prefijo en kind, Postgres UID 70, MinIO reemplazado (#57), SQLAlchemy 2.0.49 fijado, `command` explicito para emissary |
| 62 | E2E de Chaos implementado en GitHub Actions: paths, Flux/Litmus reales, pod-delete, canario, Stop/cleanup, comprobacion de permisos/admision y artefactos. Falta primer run verde; nodos/GPU/AZ siguen reservados a EKS | `.github/workflows/e2e-kind.yml`, `scripts/e2e/`, `gitops/tests/test_chaos_safety.py` |
| 65 | Promover el mismo digest desde ECR dev a staging/prod, actualizar overlays y verificar gate por entorno; `publish-ecr.yml` solo hace la publicacion inicial dev | `.github/workflows/`, `gitops/scripts/promotion/` |

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
| 15 | AWS Account ID placeholder `123456789012` en workflow | `argo-workflows/workflow-templates/model-deployment-template.yaml` | ✅ Cuenta real y repos ECR por entorno (2026-10-10) |
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
| 13 | Chaos Engineering | Phase 1 y 2 implementadas (sin ejecutar en EKS): `litmus-core` 3.31.1 + `kubernetes-chaos` 3.31.0 (antes el chart `litmus` = ChaosCenter, sin `ChaosExperiment`), exporter propio, `appkind: statefulset` para ArgoCD, WorkflowTemplates `mlflow-resilience-test` y `az-failure-test` (solo dev/staging), node-drain worker/GPU y simulacion de desalojo por zona con preflight. Particion KServe->MLflow desactivada (#59). Pendiente: ejecucion y recuperacion EKS, EC2 stop (#58), separacion de roles (#60), dashboard Grafana, SLOs, Phase 3-4. Ver [`chaos-engineering-proposal.md`](../chaos-engineering-proposal.md). | Media |

---

## Estrategia de Remediacion (Sugerida)

### Wave 1: Seguridad Critica (~4h)
- CRIT-001, CRIT-002, CRIT-003, CRIT-004

### Wave 2: Robustecimiento (~6h)
- HIGH-005 a HIGH-013 (imagenes, Python, CI)

### Wave 3: Infraestructura (~4h, requiere cuenta AWS)
- HIGH-001 a HIGH-004, MEDIUM Terraform items

### Wave 4: GitOps Completo (~8h)
- MEDIUM GitOps, Istio, Gatekeeper, Helm charts

### Wave 5: Validacion (~requiere AWS)
- e2e test, Terratest, ACM

### Wave 6: Producto (~semanas)
- Feast real, Kubecost, Model Governance, Multi-cluster

---

*Ultima actualizacion: 2026-10-20*

*Fuentes: `docs/project/critical.md`, manifiestos y scripts actuales, render de charts/overlays y pruebas locales descritas en la revision operativa. La revision no certifica un despliegue EKS.*
