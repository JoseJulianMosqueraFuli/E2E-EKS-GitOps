# Estado del Proyecto - E2E EKS GitOps

**Ultima actualizacion**: 2026-05-20
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

---

## Pendiente

### Alta prioridad

- [ ] **End-to-end test** - Requiere cuenta AWS. Validar todo el flujo: Terraform apply -> EKS deploy -> ArgoCD sync -> MLflow -> KServe inference

### Media prioridad

- [ ] **Feature Store con Feast** - No existe implementacion. Crear: feature definitions, feature server deployment, Redis/DynamoDB backend, integration con pipelines
- [ ] **Kubecost/OpenCost** - Reemplazar dashboard de costos estimados con exportador real. Dashboard actual: `k8s/mlops-stack/monitoring/dashboards/cost-monitoring-dashboard.json`
- [ ] **Certificado ACM para Ingress** - Solicitar y configurar certificado real en AWS para TLS en MLflow/KServe/Grafana
- [ ] **Backend S3 de Terraform** - Descomentar y configurar `backend "s3"` en los tres ambientes cuando se tenga cuenta AWS
- [ ] **Terratest** - Ejecutar tests de Go que ya existen en `infra/modules/*/tests/`

### Baja prioridad

- [ ] **Model Governance** - Approval workflows antes de deploy a produccion. Agregar: CRDs de approval, policies OPA/Gatekeeper, approval gates en ArgoCD
- [ ] **Multi-cluster deployment** - ArgoCD ApplicationSet con cluster generator
- [ ] **mTLS con Istio** - Comunicaciones internas cifradas entre servicios
- [ ] **OPA/Gatekeeper** - Politicas de admision avanzadas (parcialmente implementadas en `k8s/security/gatekeeper/`)
- [ ] **Teams Notifications** - Integracion con Microsoft Teams ademas de Slack
- [ ] **Tests de integracion para ML Platform** - Ampliar coverage de `ml-platform/tests/`
- [ ] **Documentar troubleshooting** - Basado en experiencia real de deploy
