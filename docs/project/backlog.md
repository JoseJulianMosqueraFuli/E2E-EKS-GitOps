# Backlog del proyecto

[← Documentation index](../README.md)

Estado y prioridades del proyecto.
Para detalles técnicos de issues CRÍTICOS y ALTOS (CVSS, fix concreto), ver: [`docs/project/critical.md`](critical.md)

---

## Revision operativa — 2026-11-08

**CI Pipeline pasa y el E2E en kind ya aprueba entrenamiento, backup/restore y Chaos (#22, `991bcd3`). El primer E2E de serving (#23, `4494aca`) fallo; la causa probable esta corregida y falta un nuevo run. El entorno AWS real sigue sin validar.** No se aplico Terraform ni se inyectaron fallos en EKS.

### Evidencia y correcciones

El [historial de implementación](../reports/implementation-history.md) conserva las correcciones,
los resultados locales y los enlaces a ejecuciones de CI. El estado por ID se mantiene abajo.

### Orden de cierre operativo

| Prioridad | Pendiente | Evidencia necesaria |
|-----------|-----------|---------------------|
| P0 | Primer verde del serving en kind (#52) | v1 servido, v2 promovido y v3 rechazado con rollback verificado a v2 |
| P0 | Configurar/aplicar AWS (#48/#50/#51/#55, HIGH-001) y completar contratos de otras apps (#49) | Plan revisado, backend activo, secretos disponibles, imagenes publicadas y ArgoCD saludable |
| P0 antes del primer apply | Add-ons compatibles con EKS 1.37 (#66), un solo dueno para EBS CSI (#67) salida de los nodos (HIGH-003) y Argo CD soportado (#76) | Versiones con soporte declarado para 1.37 renderizadas; plan sin recursos duplicados; nodos con el SG restringido que siguen descargando imagenes |
| P0 antes de fallos de zona | Recuperacion de almacenamiento y afinidades (#64) | Restore/HA entre zonas y capacidad de reubicacion demostrados; el preflight rechaza PVCs por defecto |
| P1 | Confirmar permisos, SLO/RTO/RPO y evidencia en EKS (#60/#63) | Permisos efectivos, predicciones/datos conservados, panel de resultados y tiempos medidos |
| P1 | Promocion del mismo digest ECR y ciclo completo (#65/#52/#53) | dev → staging → prod sin reconstruir; train → register → serve → monitor comprobado |
| P1 antes de actualizar datos existentes | Migrar bases MLflow/Feast | Backup verificado, upgrade del esquema MLflow y rematerializacion de Feast v3 en una nueva base online |
| P2 | Particion de red (#59), EC2 stop (#58), mTLS/Gatekeeper y Feast productivo (#34) | Aislamiento CNI, recuperacion y servicios de produccion verificados |

Detalles y comandos: [contrato de configuracion y recuperacion](../architecture/platform-runtime-config.md).

### Prueba en AWS planificada — 2026-11-15

Solo dev, en una ventana de maximo 3 horas desde `terraform apply` hasta `terraform destroy`. Objetivo: entrenar, registrar y servir `@champion` en EKS y obtener una prediccion. Fuera de alcance: Kubeflow, Feast, Istio, Gatekeeper y Litmus.

**Costo estimado** (Price List API, on-demand us-east-1, consultado el 2026-11-08): ~$0.60/h fijo con 3 × `t3.large`: EKS $0.10, nodos $0.25, 6 endpoints de interfaz × 2 AZ $0.12, 2 NAT $0.09, IPv4 $0.01, gp3 $0.025. Con redondeo por hora, la NAT por datos (~$0.45) y los logs, la ventana de 3 h cuesta ~$2–3. Despues del `destroy` solo quedan centavos al mes (estado, ECR, KMS).

**Antes de la ventana** (gratis o centavos):

1. E2E en kind en verde, incluido el serving (#52).
2. Un solo dueno para EBS CSI (#67) y 3 × `t3.large` en dev; con 2 × `t3.medium` el stack no cabe (~10 GiB de requests, maximo 17 pods por nodo).
3. Versiones de add-ons compatibles con EKS 1.37 (#66).
4. Bootstrap del backend de Terraform (HIGH-001), repos ECR creados y la imagen publicada (#55), secretos de MLflow en Secrets Manager.
5. Alerta de AWS Budgets de ~$20.

**Guion:**

| Tiempo | Paso |
|--------|------|
| 0:00–0:30 | `terraform apply` de dev |
| 0:30–1:15 | Flux, ArgoCD, MLflow, Argo Workflows, cert-manager, KServe y model-serving |
| 1:15–1:45 | Entrenar → registrar → servir y predecir |
| 1:45–2:30 | Margen para correcciones |
| 2:30 | Vaciar buckets S3 y repos ECR (sin `force_destroy`) y ejecutar `terraform destroy`, termine o no la prueba |

---

## Dashboard de Estado

| Area | Estado verificable al 2026-11-08 |
|------|--------------------------------|
| CRITICAL historicos | 4 corregidos en codigo/manifiestos; permisos efectivos de CRIT-004 pendientes de comprobar en EKS |
| HIGH historicos | 11 corregidos en codigo; HIGH-001 abierto y HIGH-003 reabierto el 2026-11-08 (el SG restringido no esta asociado a los nodos); HIGH-014 mitigado en manifiestos. HIGH-013 verificado como corregido el 2026-11-07 |
| GitOps / Chaos | Backup/restore y Chaos verdes en kind (#22, `991bcd3`); ejecucion en EKS pendiente |
| Proceso ML | Entrenamiento y gate verdes en kind; el primer E2E de serving fallo y su correccion espera un nuevo run (#52); publicacion pendiente |
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
| HIGH-002 | Kubernetes 1.28 near EOL | `infra/modules/eks/variables.tf` | ✅ Actualizado a 1.32 (2026-06-09) y a 1.37 en los tres entornos (2026-11-07), con minimo 1.35, soporte `STANDARD` y nodos AL2023. Add-ons pendientes en #66/#67 |
| HIGH-003 | Node egress sin restriccion | `infra/modules/vpc/main.tf`, `infra/modules/eks/main.tf` | Reabierto 2026-11-08: el SG `eks_nodes` restringido a `var.vpc_cidr` no esta asociado. El cluster no declara `security_group_ids` y el node group no usa launch template, asi que los nodos usan el SG que crea EKS, con salida abierta. Asociarlo exige decidir como se llega a GitHub, ghcr.io, quay.io y Docker Hub (NAT con lista de destinos o cache pull-through de ECR) y permitir el prefix list del Gateway de S3, del que ECR sirve las capas |
| HIGH-004 | CIDR hardcoded en prod | `infra/environments/prod/main.tf` | ✅ Parametrizado con `var.vpc_cidr` + `var.node_egress_cidrs` (2026-07-13); sin efecto hasta cerrar HIGH-003 |
| HIGH-005 | Feast `latest` tag | `k8s/mlops-stack/feast/feast-server.yaml` | ✅ Pineado a `0.40.1` en `gitops/applications/apps/feast/base/kustomization.yaml` (2026-06-26) |
| HIGH-006 | Imagenes de monitoring versionadas | `Dockerfile.monitoring`, `monitoring/base/` | Corregido en codigo; build/publicacion CI pendiente |
| HIGH-007 | Imagenes del pipeline principal versionadas | `argo-workflows/workflow-templates/*.yaml` | Corregido en codigo; serving E2E pendiente (#52) |
| HIGH-008 | KServe HTTP sin HTTPS redirect | `gitops/applications/apps/kserve/base/istio-config.yaml` | ✅ Agregado `tls.httpsRedirect: true` (2026-07-13). El Gateway se elimino el 2026-11-07 con KServe 0.21 `Standard`: enrutaba a un gateway Knative inexistente. Los predictores solo son internos; exposicion con TLS en #68 |
| HIGH-014 | Charts Litmus concedian acceso directo a secretos de todo el cluster | `gitops/applications/apps/chaos/base/litmus.yaml`, `rbac.yaml` | Corregido en manifiestos: eliminado administrador del catalogo; operador solo lee secretos de `litmus`. Verificar RBAC efectivo en EKS; roles de fallos aun amplios (#60). |

### Plataforma / Monitoreo (5)

| ID | Issue | Archivo(s) | Fix |
|----|-------|------------|-----|
| HIGH-009 | Grafana `emptyDir` | `gitops/applications/apps/monitoring/base/grafana-deployment.yaml` | ✅ Corregido 2026-06-08 |
| HIGH-010 | Prometheus Deployment | `gitops/applications/apps/monitoring/base/prometheus-deployment.yaml` | ✅ Corregido 2026-06-08 |
| HIGH-011 | Errores de import Python | `ml-platform/src/main.py` | ✅ Corregido 2026-06-08 |
| HIGH-012 | `fastapi`/`uvicorn` faltantes | `ml-platform/pyproject.toml` | ✅ Corregido 2026-06-08 |
| HIGH-013 | CI oculta fallas | `.github/workflows/ci.yml` | ✅ Corregido en `c50a12f` (2026-10-01); verificado 2026-11-07 sin `|| true`, `continue-on-error` ni soft-fail en test/lint. GitLab CI y CircleCI movidos a `ci-cd/future/` (inactivos) |

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

### Gatekeeper / OPA

| # | Issue | Archivo(s) |
|---|-------|------------|
| 7 | No cubre namespaces: `feast`, `models`, `ml-monitoring`, `external-secrets`, `knative-serving` | `k8s/security/gatekeeper/constraints/*.yaml` |
| 8 | PodSecurity template no verifica initContainers, runAsUser, seccompProfile a nivel pod | `k8s/security/gatekeeper/templates/pod-security.yaml` |
| 9 | IngressHosts permite `*.example.com` | `k8s/security/gatekeeper/constraints/ingress-hosts.yaml` |
| 79 | Falta instalar el controlador y los CRDs de Gatekeeper: la base solo declara ConstraintTemplates y constraints. Definir bootstrap versionado y orden de reconciliacion antes de contar con enforcement; verificar rechazo real de un pod que incumpla una politica | `gitops/applications/apps/gatekeeper/base/kustomization.yaml`, `gitops/infrastructure/` |

### GitOps / ArgoCD (8)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 45 | Argo `instanceID: argo-workflows` exige el label `workflows.argoproj.io/controller-instanceid` en cada Workflow; las WorkflowTemplates y KFP no lo ponen, por lo que el controller las ignora (confirmado en kind 2026-10-10) | `gitops/applications/apps/argo-workflows/base/configmap.yaml` | ✅ `instanceID` eliminado (un solo controller) 2026-10-10 |
| 46 | Archivo de workflows deshabilitado: requiere Postgres/MySQL (bloque `persistence` removido porque sin DB el controller no arranca) | `gitops/applications/apps/argo-workflows/base/configmap.yaml` |
| 48 | Plugin `platform-kustomize` implementado y probado desde checkout sin `aws.env`; configurar `platform-aws-config` y verificar render/sync real de ArgoCD. Una cuenta/region por instalacion | `gitops/applications/projects/mlops-applicationset.yaml`, `gitops/platform/` |
| 49 | Migrar monitoring, kubeflow y external-secrets al mecanismo `gitops/platform` (aun tienen region literal o placeholders `ACCOUNT_ID`). KServe resuelto el 2026-11-07: ya no usa IRSA ni region porque lee los modelos por el proxy de MLflow | `gitops/applications/apps/{monitoring,kubeflow,external-secrets}/` |
| 50 | Roles IRSA de Argo, MLflow, backup y lectura de secretos implementados en `workload-identity`; verificar trust y acceso S3/KMS/Secrets Manager tras aplicar Terraform. Desde la decision 2 el rol de Argo ya no publica en ECR | `infra/`, `gitops/applications/apps/argo-workflows/base/rbac.yaml` |
| 57 | MinIO dejo de publicar imagenes (Docker Hub y quay.io responden 401; repo archivado): reemplazado por Versity Gateway `versity/versitygw:v1.8.0` (S3 compatible, Apache-2). Quedan los nombres `mlflow-minio*` (Service, Secret, PVC) y menciones en docs/diagramas; renombrar a `mlflow-s3` y evaluar S3 real en dev | `gitops/applications/apps/mlflow/base/minio-*.yaml`, `docs/` |
| 58 | EC2 stop/termination sigue diferido: requiere catalogo `kube-aws`, una identidad exclusiva con alcance por tags y recuperacion demostrada. El rol de nodos actual solo modifica recursos Kubernetes | `infra/modules/eks/`, `gitops/applications/apps/chaos/base/` |
| 59 | Particion KServe→MLflow desactivada: `NAMESPACE_SELECTOR` era una allow list y las NetworkPolicies son aditivas. El add-on `vpc-cni` no define `enableNetworkPolicy`, asi que EKS hoy no aplica ninguna NetworkPolicy: activarlo, verificar el enforcement, aislar un workload desechable y probar conectividad antes/durante/despues junto con disponibilidad de inferencia | `gitops/applications/apps/chaos/experiments/pod-network-partition-kserve-mlflow.yaml`, `infra/modules/eks/` |
| 60 | Roles separados por fallo/namespace y workflows MLflow/nodo; politicas de admision restringen seleccion de cuentas y pods del fallo de borrado. Validacion efectiva y abort/cleanup incluidos en kind CI; EKS y frontera del operador privilegiado pendientes | `gitops/applications/apps/chaos/base/`, `workflows/` |
| 61 | Bootstrap completo/versionado de Flux, APIs v1/v2, rutas corregidas y espera StatefulSet de ArgoCD implementados. Runtime config obligatorio y dependencias de capas corregidas. Falta instalacion/sync desde cluster vacio verificados | `gitops/scripts/install-gitops-controllers.sh`, `gitops/infrastructure/controllers/` |
| 64 | Preflight AZ bloquea workloads con PVC en la zona objetivo y falta de CPU/memoria/GPU fuera de ella. Sigue pendiente HA/restore entre zonas y viabilidad por afinidades; PostgreSQL/gateway siguen con una replica y gp3 | `gitops/applications/apps/mlflow/`, `gitops/applications/apps/chaos/workflows/az-failure-test.yaml` |
| 68 | Exponer predictores fuera del clúster con TLS (Gateway API o Istio). Hoy solo tienen Service interno; KServe 0.21 tambien permite canary por `HTTPRoute` en modo `Standard` | `gitops/applications/apps/kserve/` |
| 69 | Retirar el chart propio `gitops/charts/kserve` (KServe 0.11), las Applications de charts que apuntan al repo de ejemplo `https://org.github.io/mlops-helm-charts` y los ejemplos de Argo que crean InferenceServices propios (`model-deployment-workflow.yaml`, `ab-test-deployment-workflow.yaml`). `make mlops-install` ya usa la app canonica | `gitops/charts/`, `gitops/applications/projects/mlops-helm-repository.yaml`, `k8s/mlops-stack/argo-workflows/examples/` |
| 71 | Serializar despliegues del mismo modelo: dos pipelines que promueven a la vez compiten por `@champion` y por la anotacion de rollout. Evaluar `synchronization.mutexes` por modelo en `ml-pipeline-template` | `gitops/applications/apps/argo-workflows/base/workflow-templates/` |
| 73 | En produccion MLflow firma URLs hacia S3 (`https://s3.AWS_REGION.amazonaws.com`). Por el Gateway endpoint eso son IPs publicas, fuera del `10.0.0.0/8:443` que permite la NetworkPolicy de MLflow, y el predictor no tenia salida a S3. Corregido en codigo el 2026-11-08: staging y prod crean un Interface endpoint de S3 con DNS privado para todo el trafico de la VPC (`enable_s3_interface_endpoint`), asi S3 responde en IPs de la VPC; el predictor de produccion recibe salida 443 al mismo bloque que MLflow. Dev conserva solo el Gateway. Ver la [decision](../architecture/platform-runtime-config.md#decision-s3-traffic-inside-the-vpc-2026-11-08). Pendiente: plan revisado y descarga real en EKS con NetworkPolicies activas (#59) | `infra/modules/vpc/main.tf`, `gitops/applications/apps/model-serving/overlays/production/` |
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
| 66 | EKS 1.37 exige actualizar add-ons fijados antes de 1.32: Istio `1.20.x` (fin de vida), AWS Load Balancer Controller `1.7.x`, EBS CSI `2.28.x` y External Secrets `0.9.13`. Los tres rangos `x` no fijan una version exacta: sustituirlos por versiones concretas verificadas al resolver la compatibilidad. Como no hay nada desplegado, se puede instalar directamente la version actual sin migracion. Cluster Autoscaler ya usa el chart `9.60.0` (CA 1.37.0, publicado 2026-11-06): revisar si hay un parche 1.37.x antes del primer apply | `gitops/infrastructure/`, `gitops/applications/apps/external-secrets/` |
| 67 | EBS CSI tiene dos duenos: `aws_eks_addon.ebs_csi_driver` en Terraform y el HelmRelease de Flux en `addons/ebs-csi-driver`. Elegir una capa y eliminar la otra antes del primer apply | `infra/modules/eks/main.tf`, `gitops/infrastructure/addons/` |
| 72 | El repositorio ECR `mlops-<env>-inference` quedo sin uso con la decision 2 (no se construyen imagenes por modelo). Decidir antes del primer apply si se elimina o se reserva para runtimes propios | `infra/environments/*/main.tf` |

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
| 52 | Serving (decisiones 1 y 2, 2026-11-07): `step serve` en la imagen `mlops-platform` sirve `@champion` con el protocolo de MLflow; KServe v0.21.0 `Standard` y cert-manager v1.21.3 por Flux. El InferenceService esta declarado en Git (app `model-serving`) y `model-deployment-template` ya no construye imagenes: hace rollout por anotacion, verifica `X-Model-Version` y paridad con el registro, y si falla devuelve el alias, hace rollback y termina en fallo. `kind-serve.sh` despliega v1, promueve v2 y rechaza v3. El primer E2E (#23, `4494aca`) fallo porque la NetworkPolicy del predictor bloqueaba la descarga desde el gateway S3; corregido, pendiente un nuevo run verde | `ml-platform/src/pipelines/`, `gitops/applications/apps/{kserve,model-serving}/`, `gitops/applications/apps/argo-workflows/base/workflow-templates/model-deployment-template.yaml`, `scripts/e2e/kind-serve.sh` |
| 53 | Dockerfile.monitoring usa Poetry/lock y Evidently compatible; imagen del servicio/CronJob versionada y build en CI. Pendiente primer build publicado y servicio saludable | `ml-platform/Dockerfile.monitoring` |

### Monitoreo (4)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 35 | ConfigMap `evidently-config` referencia key `s3_bucket` inexistente | `k8s/mlops-stack/monitoring/drift-cronjob.yaml` |
| 36 | Retencion Prometheus muy corta (200h ~ 8.3 dias) | `k8s/mlops-stack/monitoring/prometheus-stack.yaml` |
| 37 | Prometheus `web.enable-admin-api` habilitado | `gitops/charts/monitoring-stack/values.yaml` |
| 38 | Evidently image `latest` en monitoring chart | `gitops/charts/monitoring-stack/values.yaml` |
| 54 | Backup/restore reparado: PostgreSQL client + boto3, host por overlay, IRSA/bucket, contexto restricted y checksum; restore bloquea origen/base ocupada. Verde en kind CI (#22, `991bcd3`); pendiente en EKS | `gitops/applications/apps/mlflow/base/backup-cronjob.yaml` |
| 63 | Sondas funcionales implementadas: run persistente durante fallo, artefacto antes/despues y prediccion AZ con jq. Falta acordar SLO/RTO/RPO productivos, dashboard y medicion EKS; CI conserva resultados 14 dias | `gitops/applications/apps/chaos/workflows/`, `gitops/applications/apps/monitoring/` |
| 70 | Metricas y alertas de serving: se eliminaron el `ServiceMonitor` y la `PrometheusRule` de KServe porque Prometheus Operator no esta instalado. Exponer latencia/errores del predictor y alertar desde el Prometheus actual (decision 4 / fase de monitoreo) | `ml-platform/src/pipelines/serving.py`, `gitops/applications/apps/monitoring/` |
| 80 | El CronJob de drift y Evidently apuntan a `prometheus-pushgateway.monitoring:9091`, pero no existe un despliegue/Service de Pushgateway en los manifiestos. Definir la ruta de ingestion, desplegar sus dependencias y verificar que Prometheus recibe las metricas | `gitops/applications/apps/monitoring/base/drift-cronjob.yaml`, `gitops/applications/apps/monitoring/base/evidently-monitoring.yaml` |
| 81 | Prometheus `v2.48.0` y Grafana `10.2.2` siguen declarados en la base; la correccion de desincronizacion #16/#17 no actualizo esas versiones. Revisar soporte, compatibilidad y migraciones, y actualizar con versiones exactas antes del despliegue | `gitops/applications/apps/monitoring/base/prometheus-statefulset.yaml`, `gitops/applications/apps/monitoring/base/grafana-deployment.yaml` |

### CI/CD (5)

| # | Issue | Archivo(s) |
|---|-------|------------|
| 39 | GitLab CI usa `bitnami/kubectl:latest` y `bridgecrew/checkov:latest` | `ci-cd/future/gitlab/.gitlab-ci.yml` | Diferido: proveedor inactivo desde 2026-11-07; requisito para reactivarlo |
| 40 | CircleCI usa `bitnami/kubectl:latest` | `ci-cd/future/circleci/config.yml` | ✅ Ya no aplica: el executor usa `cimg/go:1.21`; proveedor inactivo desde 2026-11-07 |
| 41 | GitHub Actions: pytest/flake8/black con `|| true` | `.github/workflows/ci.yml` | ✅ Corregido en `c50a12f` (HIGH-013) |
| 42 | GitLab CI: pytest/flake8/black con `|| true` | `ci-cd/future/gitlab/.gitlab-ci.yml` | ✅ Corregido en `c50a12f`; proveedor inactivo |
| 43 | CircleCI: pytest/flake8/black con `|| true` | `ci-cd/future/circleci/config.yml` | ✅ Corregido en `c50a12f`; proveedor inactivo |
| 44 | Falta pipeline automatizada para Terratest Go | `.github/workflows/ci.yml` |
| 55 | Rol OIDC por entorno y publicacion inicial dev en `publish-ecr.yml` implementados. Configurar provider/variables del entorno GitHub, aplicar IAM y ejecutar; promocion sin reconstruir en #65 | `.github/workflows/ml-platform-image.yml`, `infra/` |
| 56 | Primer run verde de `e2e-kind.yml` (entrena, evalua, registra y bloquea por el gate de promocion) | `.github/workflows/e2e-kind.yml`, `scripts/e2e/kind-smoke.sh` | ✅ Verde en `2ca2b2e` (2026-10-11): Secrets sin prefijo en kind, Postgres UID 70, MinIO reemplazado (#57), SQLAlchemy 2.0.49 fijado, `command` explicito para emissary |
| 62 | E2E de Chaos implementado en GitHub Actions: paths, Flux/Litmus reales, pod-delete, canario, Stop/cleanup, comprobacion de permisos/admision y artefactos. Primer verde en kind (#22, `991bcd3`); nodos/GPU/AZ siguen reservados a EKS | `.github/workflows/e2e-kind.yml`, `scripts/e2e/`, `gitops/tests/test_chaos_safety.py` |
| 74 | Corregido en codigo 2026-11-08: `publish-ecr.yml` construye las tres imagenes en el runner, las escanea con Trivy y solo hace push si ninguna tiene vulnerabilidades CRITICAL/HIGH con arreglo; `ml-platform-image.yml` escanea las mismas imagenes en cada PR. Los Dockerfiles aplican `apt-get upgrade` en la etapa final para no heredar parches de Debian pendientes. Pendiente: primer run de ambos workflows | `.github/workflows/ml-platform-image.yml`, `.github/workflows/publish-ecr.yml`, `ml-platform/Dockerfile*` |
| 75 | Corregido en codigo 2026-11-08: `trivy config` paso de 69 a 0 hallazgos HIGH/CRITICAL. Sin `gitops-admin` (sin uso, leia secretos del cluster), sin ConfigMaps `irsa-policy-*` (IAM duplicado de Terraform), argo-server sin `pods/exec` ni acceso a secretos (`--auth-mode=client`; SSO #47 necesitara un Role propio), notificaciones de ArgoCD limitadas a su namespace, contenedores con raiz de solo lectura, sin escalada, `drop ALL` y no root, ECR inmutable y subredes publicas sin IP publica. Las excepciones restantes estan justificadas en `.trivyignore.yaml`. CI bloquea dependencias vulnerables con arreglo y configuraciones nuevas. Feast y monitoring solo validados estaticamente | `gitops/`, `infra/modules/{ecr,vpc}/`, `.trivyignore.yaml`, `.github/workflows/ci.yml` |
| 76 | Argo CD esta fijado en v2.9.3 (`gitops/infrastructure/controllers/argocd/kustomization.yaml` y el sidecar del plugin), una version sin soporte con CVEs criticas publicadas. Actualizar a una version soportada antes del primer despliegue y revisar los cambios incompatibles de 3.x. La kustomization no renderizaba (parches con namespace y `argocd-rbac-cm` duplicado); corregido el 2026-11-08 | `gitops/infrastructure/controllers/argocd/` |
| 77 | La app `monitoring` despliega un segundo `argocd-notifications-controller` aunque Argo CD 2.3+ ya trae el suyo; su ConfigMap `dev-argocd-notifications-cm` nunca se lee por el prefijo. Quitar el duplicado y configurar `argocd-notifications-cm` del controlador oficial | `gitops/applications/apps/monitoring/base/argocd-notifications.yaml`, `gitops/infrastructure/controllers/argocd/` |
| 78 | Los controladores de Flux aplican cualquier recurso con un rol amplio (excepcion KSV-0046). Evaluar `serviceAccountName` por Kustomization/HelmRelease con roles por capa y `--no-cross-namespace-refs` | `gitops/infrastructure/controllers/flux-system/` |
| 82 | Quedan YAML locales de los cuatro controladores de Flux con imagenes antiguas; la kustomization activa solo referencia el instalador v2.7.5. Retirar archivos sin uso y ajustar las pruebas que aun exigen su existencia, comprobando que el bootstrap conserva todos los controladores | `gitops/infrastructure/controllers/flux-system/`, `gitops/tests/test_gitops_checkpoint.py`, `gitops/tests/test_repository_structure.py` |
| 83 | Migracion a Python 3.14.10 implementada en las tres imagenes y CI de ML; proyecto y lock admiten `>=3.11,<3.15`. Servidor MLflow usa `psycopg2-binary==2.9.11`, con wheel compatible. Dependabot excluye `>=3.15` por incompatibilidades del stack. Instalacion del lock y resolucion de binarios Linux amd64 verificadas; 203 pruebas ML aprobadas en Python 3.14.10 con backend grafico Agg, tres pruebas del contrato imagen/proyecto/CI aprobadas y Black/Flake8 sin errores. Pendiente: build completo y E2E en GitHub Actions | `ml-platform/Dockerfile*`, `ml-platform/pyproject.toml`, `ml-platform/poetry.lock`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `gitops/tests/test_python_runtime_contract.py` |
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
| 10 | Troubleshooting guide | ✅ [`docs/troubleshooting.md`](../troubleshooting.md) con los fallos reales del E2E en kind (2026-11-07). Ampliar con los del primer despliegue en EKS | Baja |
| 11 | Actualizar pre-commit hooks | detect-secrets, terraform_fmt, etc. | Baja |
| 12 | Actualizar versiones EKS addons | Fijar versiones de EBS CSI, VPC CNI, etc. | Baja |
| 13 | Chaos Engineering | Phase 1 y 2 implementadas (sin ejecutar en EKS): `litmus-core` 3.31.1 + `kubernetes-chaos` 3.31.0 (antes el chart `litmus` = ChaosCenter, sin `ChaosExperiment`), exporter propio, `appkind: statefulset` para ArgoCD, WorkflowTemplates `mlflow-resilience-test` y `az-failure-test` (solo dev/staging), node-drain worker/GPU y simulacion de desalojo por zona con preflight. Particion KServe->MLflow desactivada (#59). Pendiente: ejecucion y recuperacion EKS, EC2 stop (#58), separacion de roles (#60), dashboard Grafana, SLOs, Phase 3-4. Ver [propuesta de Chaos](../proposals/chaos-engineering.md). | Media |

---

*Última revisión editorial: 2026-11-09. Estados técnicos conservados de la revisión operativa.*

*Fuentes: `docs/project/critical.md`, manifiestos y scripts actuales, render de charts/overlays y pruebas locales descritas en la revision operativa. La revision no certifica un despliegue EKS.*
