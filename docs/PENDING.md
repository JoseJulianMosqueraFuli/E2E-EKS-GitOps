# Estado del Proyecto - E2E EKS GitOps

**Ultima actualizacion**: 2026-06-06
**Regla**: Actualizar este archivo con cada cambio significativo. Poner fecha en cada item marcado.

---

## Completado

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
- [x] Reporte de auditoria completa - Revison de 120+ archivos, 6000+ lineas, hallazgos mapeados en `critical.md` y `backlog.md` `(2026-06-06)`
- [x] Feature Store con Feast (parcial) - Feature repo local: definiciones en feature_definitions.py, datos parquet (model_features, transaction_stats, user_profile), online_store.db, registry.db, tests unitarios. Falta: backend productivo (Redis/DynamoDB), server K8s `(2026-06-07)`

---

## Pendiente

### Critico (Bloqueantes para produccion)

Ver **`critical.md`** en la raiz del proyecto para detalles completos con CVSS, fix concreto y owner.

- [x] **CRIT-001**: Argo Workflows TLS deshabilitado (`--secure=false`) -> corregido a `--secure=true` (`2026-06-07`)
- [x] **CRIT-002**: Argo Workflows auth basica (`--auth-mode=server`) -> corregido a `--auth-mode=sso` (`2026-06-07`)
- [x] **CRIT-003**: Argo Workflows executor docker obsoleto + montaje de `docker.sock` -> corregido a `emissary`, eliminado `hostPath` del socket (`2026-06-07`)
- [ ] **CRIT-004**: ArgoCD AppProject `mlops-core` excesivamente permisivo (`*`, `*`, `*`)

### Alta prioridad

- [ ] **HIGH-001**: Backend local Terraform (sin S3+DynamoDB) en los 3 ambientes — **Procedimiento documentado en cada `main.tf`, requiere cuenta AWS para activar**
- [x] **HIGH-002**: Kubernetes 1.28 cerca de EOL -> actualizado a 1.32 (2026-06-09)
- [ ] **HIGH-003**: Egress de nodos EKS sin restriccion (`0.0.0.0/0`) en dev/staging
- [ ] **HIGH-004**: CIDR `10.0.0.0/8` hardcodeado en prod para egress de nodos
- [x] **HIGH-005**: Feast `latest` pineado a `0.40.1` (`2026-06-26`)
- [ ] **HIGH-006 a HIGH-007**: Imagenes con tag `:latest` en Evidently y workflow templates de Argo
- [ ] **HIGH-008**: KServe HTTP sin redireccion automatica a HTTPS
- [ ] **HIGH-009**: Grafana usa `emptyDir` (perdida de datos al reiniciar)
- [ ] **HIGH-010**: Prometheus como Deployment en lugar de StatefulSet (perdida de datos)
- [ ] **HIGH-011**: Errores de importacion en `ml-platform/src/main.py` (`sys.exit` sin import, prefijo `src.` faltante)
- [ ] **HIGH-012**: `fastapi` y `uvicorn` no declarados en `pyproject.toml`
- [ ] **HIGH-013**: CI/CD pipelines ocultan fallas con `|| true` (pytest, flake8, black)
- [ ] **End-to-end test** - Requiere cuenta AWS. Validar todo el flujo: Terraform apply -> EKS deploy -> ArgoCD sync -> MLflow -> KServe inference

### Media prioridad

**Seguridad e Istio:**
- [ ] Istio mTLS incompleto: falta STRICT en `models`, `ml-monitoring`, `external-secrets`, `knative-serving`
- [ ] Istio AuthorizationPolicies: falta default-deny en `argo-workflows`, `feast`, `kubeflow`, `models`
- [ ] Istio: falta allow para health checks y Prometheus scrape en todos los namespaces
- [ ] Istio: falta allow para `argo-workflows` -> MLflow y `kubeflow` -> KServe
- [ ] Gatekeeper no cubre namespaces: `feast`, `models`, `ml-monitoring`, `external-secrets`, `knative-serving`
- [ ] Gatekeeper template PodSecurity no verifica initContainers, runAsUser, ni seccompProfile a nivel de pod
- [ ] Gatekeeper constraint IngressHosts permite `*.example.com` (demasiado permisivo)
- [ ] NetworkPolicy falta para namespaces: `feast`, `argo-workflows`, `ml-monitoring`

**GitOps y Consistencia:**
- [x] Unificar fuente de verdad: `monitoring`, `argo-workflows`, `feast`, `secrets`, `gatekeeper`, `istio` en `k8s/` ahora apuntan a `gitops/applications/apps/` (`2026-06-26`)
- [x] Crear Applications de ArgoCD para: `feast`, `argo-workflows`, `external-secrets`, `gatekeeper`, `istio` (`2026-06-26`)
- [x] Desincronizacion de versiones: Prometheus `v2.45.0` vs `v2.48.0`, Grafana `10.0.3` vs `10.2.2` alineadas a `v2.48.0` y `10.2.2` (`2026-06-26`)
- [x] Duplicacion de alertas Prometheus entre `k8s/` y `gitops/`: consolidado en `gitops/applications/apps/monitoring/base/` (`2026-06-26`)
- [x] ApplicationSet `mlops-applicationset` ahora genera apps para `argo-workflows`, `feast`, `external-secrets`, `gatekeeper`, `istio` (`2026-06-26`)
- [x] Applications individuales por ambiente eliminadas; el ApplicationSet es el mecanismo canonical (`2026-06-26`)
- [x] Manifiestos duplicados en `k8s/` eliminados; `gitops/applications/apps/<app>/base/` es la única fuente de verdad (`2026-06-26`)

**Helm Charts:**
- [ ] MLflow chart usa `python:3.11-slim` en vez de imagen oficial MLflow
- [ ] KServe chart: `urlScheme: "http"` deberia ser `https`
- [ ] KServe chart deshabilita `NetworkPolicy` y `PDB`
- [ ] Kubeflow chart usa Argo workflow controller `v3.3.10` (muy antiguo, actualizar)

**Infraestructura:**
- [ ] KMS en dev sin `enable_key_rotation` (inconsistencia con staging/prod)
- [ ] EKS addon `vpc_cni` sin IRSA asignado (a diferencia de EBS CSI)
- [ ] `allowed_principals` vacio por defecto en modulo ECR (policy invalida si no se sobreescribe)
- [ ] `node_group_desired_size` sin validacion contra min/max
- [ ] Glue table schema hardcodeado (`feature_1`, `feature_2`, `target`)
- [ ] Glue crawlers schedule hardcodeado igual en los 3 ambientes

**Plataforma ML:**
- [ ] `prometheus-client` inconsistente entre `pyproject.toml` (<0.17) y `Dockerfile.monitoring` (0.17.1)
- [ ] `LabelEncoder` incompatible con `ColumnTransformer` en `feature_engineering.py`
- [x] Duplicacion de clase `ModelMonitor` (`src/utils/monitoring.py` vs `src/monitoring/model_monitor.py`) - eliminado `src/utils/monitoring.py` (`2026-07-13`)
- [x] Transformers custom (`DateTimeFeatureExtractor`, `OutlierClipper`, etc.) definidos pero nunca usados - eliminada clase `CustomTransformers` de `feature_engineering.py` (`2026-07-13`)
- [x] `dvc`, `awscli`, `kubernetes` declarados en `pyproject.toml` pero sin uso evidente en el codigo - removidos (`2026-07-13`)
- [x] `awscli` como dependencia de libreria (es una CLI, no deberia estar en un paquete Python) - removido (`2026-07-13`)
- [ ] Feast feature repo: falta backend productivo (Redis/DynamoDB) y server deployment en K8s

**Monitoreo:**
- [ ] ConfigMap `evidently-config` referenciado en drift-cronjob no tiene la key `s3_bucket`
- [ ] Retencion de Prometheus muy corta: `storage.tsdb.retention.time=200h` (~8.3 dias)
- [ ] Prometheus `web.enable-admin-api` habilitado (potencialmente inseguro)
- [ ] Evidently image usa `latest` en chart de monitoreo

**CI/CD:**
- [ ] GitLab CI: `bitnami/kubectl:latest` (pinear version)
- [ ] CircleCI: `bitnami/kubectl:latest` (pinear version)
- [ ] GitHub Actions CI: `pytest ... || true`, `flake8 ... || true`, `black ... || true`
- [ ] GitLab CI: `pytest ... || true`, `flake8 ... || true`, `black ... || true`
- [ ] CircleCI: `pytest ... || true`, `flake8 ... || true`, `black ... || true`
- [ ] Falta pipeline automatizada para ejecutar Terratest de Go

### Baja prioridad

- [ ] **Feature Store con Feast** - Backend productivo (Redis/DynamoDB), server deployment en K8s, integracion con pipelines de training
- [ ] **Kubecost/OpenCost** - Reemplazar dashboard de costos estimados con exportador real
- [ ] **Certificado ACM para Ingress** - Solicitar y configurar certificado real en AWS
- [ ] **Terratest** - Ejecutar tests de Go que ya existen en `infra/modules/*/tests/`
- [ ] **Model Governance** - Approval workflows antes de deploy a produccion
- [ ] **Multi-cluster deployment** - ArgoCD ApplicationSet con cluster generator
- [ ] **Teams Notifications** - Integracion con Microsoft Teams ademas de Slack
- [ ] **ArgoCD Image Updater** - Bumps automaticos desde ECR / GHCR
- [ ] **Tests de integracion para ML Platform** - Ampliar coverage
- [ ] **Documentar troubleshooting** - Basado en experiencia real de deploy
- [ ] **VPA** (VerticalPodAutoscaler) para recomendaciones de recursos en MLflow, KServe, etc.
- [ ] **HPA y PDB** faltantes para Feast server, Argo Workflows server
- [ ] **ServiceMonitor** faltante para Feast
- [ ] **Pre-commit hooks**: actualizar versiones antiguas de detect-secrets y otros hooks

---

## Proximos pasos recomendados (cuando se retome el proyecto)

1. **Fase Seguridad**: Resolver CRIT-001 a CRIT-004 (4h de trabajo estimado)
2. **Fase Correcciones Rapidas**: HIGH-005 a HIGH-013 (imagenes latest, Python fixes, CI fixes) (~6h)
3. **Fase Infra**: Backend S3, upgrade Kubernetes, egress restringido (~4h, requiere cuenta AWS)
4. **Fase GitOps**: Unificar fuentes de verdad, completar Istio/Gatekeeper, crear apps faltantes (~8h)
5. **Fase Validacion**: e2e test en AWS (~requiere cuenta AWS)
6. **Fase Extras**: Feast real, Kubecost, ACM, Model Governance, Multi-cluster (~varias semanas)

---

**Score estimado tras cada fase:**
- Actual (sin fixes): ~85/100
- Post Fase 1 (Críticos): ~91/100
- Post Fase 2 (Altos): ~96/100
- Post Fase 3+4 (Medios + GitOps): ~98/100
- Post Fase 5+6 (e2e + Extras): ~99/100
