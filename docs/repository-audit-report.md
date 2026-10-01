# Auditoría del repositorio E2E-EKS-GitOps

**Fecha:** 2026-10-01  
**Alcance:** fases 1 a 4: arquitectura, Terraform/AWS, Kubernetes/GitOps y CI/CD  
**Tipo:** análisis estático del repositorio; no se aplicaron recursos en AWS ni en Kubernetes.

## 1. Resumen ejecutivo

El repositorio presenta una arquitectura ambiciosa y bien orientada para una plataforma MLOps sobre Amazon EKS. La separación conceptual es adecuada:

```text
Terraform → Amazon EKS → Flux (infraestructura) → ArgoCD (aplicaciones)
                                              ↓
                 MLflow → Kubeflow/Argo Workflows → KServe → Monitoring
```

Sus principales fortalezas son la cobertura de extremo a extremo, la separación por entornos, los módulos Terraform reutilizables, la observabilidad y la incorporación de controles de seguridad.

La auditoría también encontró inconsistencias que deben resolverse antes de considerar el flujo operativo como reproducible:

1. La configuración de Flux referencia una URL externa en los tres clusters, mientras que ArgoCD usa este repositorio. Las ramas también difieren en dev: Flux usa `dev` y ArgoCD usa `develop`.
2. La ruta `gitops/applications/environments/` no existe en el checkout analizado, aunque el script de promoción la requiere; no es una ruta canónica documentada para las aplicaciones actuales.
3. La mayoría de validaciones CI son no bloqueantes por el uso de `|| true`, `allow_failure` o `soft-fail`.
4. El AppProject de ArgoCD permite repositorios, namespaces y recursos mediante comodines.
5. Persisten imágenes con tag `latest`, lo que impide despliegues reproducibles.
6. Terraform no pudo ser ejecutado localmente porque el binario `terraform` no está instalado en el entorno de análisis.

**Conclusión:** el diseño conceptual es claro, pero el camino real desde commit hasta despliegue necesita una fase de reconciliación y endurecimiento.

## 2. Fase 1 — Inventario y arquitectura

### Componentes identificados

| Área | Ubicación | Responsabilidad |
|---|---|---|
| Infraestructura AWS | `infra/modules/`, `infra/environments/` | VPC, EKS, S3, ECR, Glue, KMS e IAM |
| Infraestructura GitOps | `gitops/infrastructure/` | Flux, add-ons, networking y seguridad del cluster |
| Aplicaciones GitOps | `gitops/applications/apps/` | Bases y overlays Kustomize para MLOps |
| Charts | `gitops/charts/` | Charts Helm propios |
| ML | `ml-platform/src/` | Datos, modelos, pipelines, CLI y monitorización |
| Kubernetes legacy/compatibilidad | `k8s/` | Manifiestos y punteros históricos |
| CI/CD | `.github/workflows/`, `.gitlab-ci.yml`, `.circleci/`, `ci-cd/` | Validación, promoción y Jenkins |

### Fuentes canónicas

La documentación declara `gitops/applications/apps/<app>/base/` como fuente de verdad para las aplicaciones (`gitops/applications/README.md:5-6`). Los manifiestos bajo `k8s/` deberían ser únicamente punteros de compatibilidad. Esta regla es buena, pero debe validarse automáticamente para evitar divergencias.

### Flujo previsto

1. Terraform crea la red, el cluster EKS, almacenamiento, registros y servicios AWS.
2. Flux reconcilia la infraestructura del cluster.
3. ArgoCD genera aplicaciones mediante `ApplicationSet`.
4. Cada aplicación usa el overlay del entorno correspondiente.
5. MLflow registra experimentos y modelos.
6. Kubeflow/Argo Workflows ejecutan procesos ML.
7. KServe sirve modelos.
8. Prometheus, Grafana y Evidently observan la plataforma.

### Inconsistencia crítica encontrada

`gitops/infrastructure/clusters/{dev,staging,production}/flux-system/gotk-sync.yaml:9,12,21` referencia respectivamente las ramas `dev`, `staging` y `main`, pero siempre usa la URL `ssh://git@github.com/org/gitops-infrastructure`. En cambio, `gitops/applications/projects/mlops-applicationset.yaml:44-57,73-75` usa las ramas `develop`, `staging`, `main` y el repositorio `JoseJulianMosqueraFuli/E2E-EKS-GitOps.git`.

Esto puede impedir que Flux reconcilie el repositorio esperado y además produce una diferencia de rama en dev. Debe confirmarse si la URL `org/gitops-infrastructure` es intencional para un repositorio separado o si quedó como placeholder de bootstrap.

## 3. Fase 2 — Terraform y AWS

### Estado estructural

Existen tres raíces Terraform (`infra/environments/dev`, `staging` y `prod`) y módulos reutilizables para VPC, EKS, S3, ECR y Glue. La configuración de desarrollo incluye KMS con rotación habilitada (`infra/environments/dev/main.tf:60-72`) y restringe el egress de nodos a la VPC más CIDR adicionales (`:74-87`).

EKS tiene endpoint público deshabilitado en dev (`infra/environments/dev/main.tf:90-103`), lo que es positivo para reducir exposición, aunque requiere una ruta operativa de administración dentro de la VPC.

### Riesgos y observaciones

| Severidad | Hallazgo | Evidencia |
|---|---|---|
| Alta | Backend S3 está comentado; el estado local no ofrece locking ni colaboración segura | `infra/environments/dev/main.tf:12-34` |
| Media | ECR de dev usa tags mutables | `infra/environments/dev/main.tf:180-203` |
| Pendiente | No se pudo ejecutar `terraform fmt` porque Terraform no está instalado en el entorno | Validación local del 2026-10-01 |
| Pendiente | No se ejecutó `terraform validate/plan` ni se accedió a AWS | Alcance de esta auditoría |

### Validaciones recomendadas

En un runner con Terraform instalado:

```bash
terraform fmt -check -recursive infra
cd infra/environments/dev && terraform init -backend=false && terraform validate
cd infra/environments/dev && terraform plan -input=false
```

Después debe repetirse para `staging` y `prod`. El `plan` real requiere revisar credenciales, estado remoto y costos antes de ejecutar.

## 4. Fase 3 — Kubernetes y GitOps

### Cobertura

El `ApplicationSet` define diez aplicaciones y las combina con tres entornos (`gitops/applications/projects/mlops-applicationset.yaml:7-58`). Dev y staging tienen auto-sync y pruning; producción conserva auto-sync pero desactiva pruning automático (`:79-95`). Esta diferenciación es razonable.

Las aplicaciones cubren MLflow, Kubeflow, KServe, monitoring, Argo Workflows, Feast, External Secrets, Gatekeeper, Istio y chaos engineering.

### Riesgos confirmados

| Severidad | Hallazgo | Evidencia |
|---|---|---|
| Crítica | Cualquier repositorio puede ser fuente de ArgoCD | `gitops/applications/projects/mlops-core.yaml:11-12` |
| Crítica | Cualquier namespace puede ser destino | `gitops/applications/projects/mlops-core.yaml:14-26` |
| Crítica | Se permiten todos los recursos de cluster y namespace | `gitops/applications/projects/mlops-core.yaml:28-34` |
| Alta | Existen imágenes `latest` en workflows, Feast y monitoring | `gitops/applications/apps/argo-workflows/base/workflow-templates/`, `gitops/applications/apps/feast/base/feast-server.yaml`, `gitops/applications/apps/monitoring/base/` |
| Alta | El script de promoción espera `gitops/applications/environments/`, pero esa ruta no existe en el checkout y las aplicaciones actuales están bajo `gitops/applications/apps/` | `gitops/scripts/promotion/promote.py:94-110`; `gitops/applications/README.md:5-6`; verificación de estructura 2026-10-01 |

### Validaciones ejecutadas

Se enumeraron diez overlays de desarrollo bajo `gitops/applications/apps/*/overlays/dev`. No se ejecutó `kustomize build` en este entorno; los builds deben cubrir todos los overlays, no únicamente dev. La presencia de un directorio no demuestra que el manifiesto renderice correctamente.

### Ownership recomendado

Debe documentarse y validarse una frontera explícita:

- **Flux:** `gitops/infrastructure/` y recursos de infraestructura del cluster.
- **ArgoCD:** `gitops/applications/` y aplicaciones MLOps.

No debe existir el mismo recurso administrado por ambos controladores.

## 5. Fase 4 — CI/CD y promoción

### GitHub Actions

`.github/workflows/ci.yml` contiene jobs para Terraform, Terratest, Kubernetes, ML Platform, seguridad, Helm y scripts. La cobertura es amplia, pero sus resultados no son confiables como gate porque múltiples comandos terminan en `|| true` (`.github/workflows/ci.yml:29-39,62-69,92-111,133-146,196-203`).

### GitLab y CircleCI

El mismo patrón aparece en `.gitlab-ci.yml:25-27,42,57-58,83-98` y `.circleci/config.yml:26-30,46,61-86`. GitLab además declara `allow_failure: true` para linting (`.gitlab-ci.yml:86-98`), y Checkov usa `--soft-fail` en ambos pipelines.

Estos workflows son útiles como plantillas multi-proveedor, pero actualmente funcionan más como observabilidad que como protección de calidad.

### Jenkins

Jenkins sí tiene una ruta de despliegue explícita (`ci-cd/providers/jenkins/Jenkinsfile:68-80`) y ejecuta Terraform con plan y apply cuando se activa el parámetro correspondiente. Sin embargo, las etapas de validación y entrenamiento contienen TODOs (`:84-123`), por lo que no representan todavía un flujo ML completo.

### Promoción

El workflow de promoción valida YAML y tests seleccionados, pero ejecuta:

```bash
python promote.py dev staging --dry-run
python promote.py staging production --dry-run
```

Esto está en `.github/workflows/environment-promotion.yml:108-111,156-159`. El modo dry-run solamente informa cambios; no escribe los archivos que la pull request debería transportar. Además, `promote.py:94-110` requiere directorios de entorno que no existen en el checkout analizado. El flujo debe probarse con una pull request real y un diff no vacío antes de considerarse operativo.

## 6. Ventajas del proyecto

1. Cobertura completa del ciclo MLOps.
2. Separación modular entre infraestructura, cluster y aplicaciones.
3. Entornos dev/staging/production con políticas distintas.
4. ApplicationSet para evitar definiciones repetidas de aplicaciones.
5. Monitorización, alertas y detección de drift.
6. Controles de seguridad integrados en el diseño.
7. Pruebas Python, Hypothesis y Terratest disponibles.
8. Documentación centralizada en `docs/README.md`.
9. Interfaz operativa unificada mediante `Makefile`.
10. Posibilidad de desarrollo ML local sin AWS.

## 7. Matriz de prioridades

| Prioridad | Acción | Tipo |
|---|---|---|
| P0 | Restringir `sourceRepos`, destinos y whitelist del AppProject ArgoCD | Seguridad |
| P0 | Corregir la referencia de Flux o confirmar que es un bootstrap de ejemplo | Operación |
| P0 | Resolver la ausencia de `gitops/applications/environments/` o actualizar el script de promoción | Correctitud |
| P1 | Eliminar `|| true`, `allow_failure` y `soft-fail` de gates obligatorios | CI/CD |
| P1 | Hacer que la promoción genere cambios reales y usar aprobación protegida para producción | CI/CD |
| P1 | Fijar imágenes a versiones semánticas o digests | Supply chain |
| P1 | Activar backend Terraform remoto con locking antes del uso compartido | Infraestructura |
| P2 | Validar todos los overlays con Kustomize y todos los charts con Helm | Calidad |
| P2 | Añadir una prueba automática de ownership Flux/ArgoCD | GitOps |
| P2 | Ejecutar un E2E real Terraform → EKS → GitOps → MLflow → KServe | Plataforma |

## 8. Plan de mejora por tareas

1. Crear un job de inventario que compruebe rutas canónicas y enlaces internos.
2. Añadir una matriz CI para construir cada overlay de cada entorno.
3. Instalar Terraform, Kustomize, Helm y kubectl en runners versionados.
4. Convertir las validaciones críticas en pasos bloqueantes.
5. Añadir un test que compare ramas, repositorios y paths de Flux y ArgoCD.
6. Restringir el AppProject y probar los permisos con manifests mínimos.
7. Rehacer la promoción para que produzca un diff verificable y una PR no vacía.
8. Migrar Terraform a S3 con locking y documentar el procedimiento por entorno.
9. Fijar imágenes y añadir escaneo de manifests renderizados.
10. Ejecutar una prueba E2E controlada y publicar sus resultados.

## 9. Límites del análisis

- No se aplicaron cambios en AWS ni Kubernetes.
- No se pudo ejecutar Terraform localmente porque el binario no está instalado en este entorno de análisis; esto no demuestra un fallo de la configuración Terraform.
- No se confirmó conectividad a un cluster EKS.
- La auditoría estática no sustituye un `terraform plan` autenticado, un build completo de Kustomize/Helm ni una ejecución real de GitHub Actions.
