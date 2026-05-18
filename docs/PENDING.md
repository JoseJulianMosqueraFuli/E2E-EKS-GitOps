# Estado del Proyecto - E2E EKS GitOps

**Ultima actualizacion**: 2026-05-18
**Regla**: Actualizar este archivo con cada cambio significativo. Poner fecha en cada item marcado.

---

## Completado

- [x] Model Monitoring con Evidently - Detectar data drift y model drift automaticamente `(2026-05-16)`
- [x] Dashboards de Grafana pre-configurados - Para MLflow, KServe, y metricas de modelos `(2026-05-16)`
- [x] ArgoCD - GitOps real para deployment continuo `(2026-05-16)` - Controller, AppProject, ApplicationSet, overlays por ambiente, Helm charts, RBAC, ingress
- [x] Slack Notifications - Hook en ArgoCD annotations + Python notifier + Jenkins slackSend `(2026-05-16)` - Parcial: falta deployar Alertmanager config y ArgoCD Notifications Controller
- [x] Cost Monitoring - Dashboard de Grafana con costos estimados `(2026-05-16)` - Parcial: falta exportador real (Kubecost/OpenCost)
- [x] Auto-retraining Pipeline - Template de 7 pasos con DAG y logica condicional `(2026-05-16)` - Parcial: usa valores simulados, no carga modelos reales de MLflow
- [x] CI/CD - GitHub Actions (CI + promotion) + Jenkins pipeline + promotion script con validacion `(2026-05-16)`
- [x] Staging/Prod environments - Terraform + GitOps overlays existen `(2026-05-16)` - Parcial: son copia de dev sin hardening productivo

---

## Pendiente

### Alta prioridad

- [ ] **Hardening de staging/prod** - Variables.tf dicen "Development Environment", nodos t3.medium iguales a dev, sin ajustes de produccion (replicas, recursos, seguridad). Archivos: `infra/environments/staging/`, `infra/environments/prod/`, `gitops/applications/environments/`
- [ ] **Deployar Alertmanager config** - Crear ConfigMap con routing real de alertas a Slack/Teams. Referencia: `k8s/mlops-stack/monitoring/prometheus-stack.yaml`, `docs/PHASE2_IMPLEMENTATION_GUIDE.md`
- [ ] **Deployar ArgoCD Notifications Controller** - Las annotations de Slack estan en los Applications pero falta instalar el controller y configurar el secret con el webhook
- [ ] **Auto-retraining con valores reales** - Los 7 pasos del template usan `python:3.9-slim` con `pip install` en runtime y valores hardcoded. Conectar a MLflow real para cargar modelos y metricas. Archivo: `k8s/mlops-stack/argo-workflows/workflow-templates/model-retraining-template.yaml`
- [ ] **End-to-end test** - Requiere cuenta AWS. Validar todo el flujo: Terraform apply -> EKS deploy -> ArgoCD sync -> MLflow -> KServe inference

### Media prioridad

- [ ] **Feature Store con Feast** - No existe implementacion. Solo mencion en docs como recomendacion. Ni siquiera esta en requirements.txt. Crear: feature definitions, feature server deployment, Redis/DynamoDB backend, integration con pipelines
- [ ] **A/B Testing Framework** - KServe tiene campos canary pero no hay framework de experimentacion (asignacion de usuarios, metricas estadisticas, decision automática). Archivo base: `k8s/mlops-stack/argo-workflows/examples/model-deployment-workflow.yaml` (tiene placeholder de Istio VirtualService)
- [ ] **Kubecost/OpenCost** - Reemplazar dashboard de costos estimados con exportador real. Dashboard actual: `k8s/mlops-stack/monitoring/dashboards/cost-monitoring-dashboard.json`
- [ ] **Certificado ACM para Ingress** - Solicitar y configurar certificado real en AWS para TLS en MLflow/KServe/Grafana
- [ ] **Backend S3 de Terraform** - Descomentar y configurar `backend "s3"` en los tres ambientes cuando se tenga cuenta AWS
- [ ] **Terratest** - Ejecutar tests de Go que ya existen en `infra/modules/*/tests/`

### Baja prioridad

- [ ] **Model Governance** - Approval workflows antes de deploy a produccion. Actualmente solo `--approve` flag manual en `gitops/scripts/promotion/promote.py`. Agregar: CRDs de approval, policies OPA/Gatekeeper, approval gates en ArgoCD
- [ ] **Multi-cluster deployment** - Deploy modelos a multiples regiones. Requiere: ClusterSet API, KubeFed o ArgoCD ApplicationSet con cluster generator
- [ ] **mTLS con Istio** - Comunicaciones internas cifradas entre servicios
- [ ] **OPA/Gatekeeper** - Politicas de admision avanzadas (no ejecutar como root, limitar recursos, etc.)
- [ ] **Teams Notifications** - Integracion con Microsoft Teams ademas de Slack
- [ ] **Tests de integracion para ML Platform** - Ampliar coverage de `ml-platform/tests/`
- [ ] **Documentar troubleshooting** - Basado en experiencia real de deploy