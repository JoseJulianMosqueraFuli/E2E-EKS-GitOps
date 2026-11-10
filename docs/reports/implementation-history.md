# Historial de implementación y validación

[Índice](../README.md) · [Backlog vigente](../project/backlog.md)

Registro histórico trasladado del backlog el 2026-11-09. Los resultados, versiones y pendientes
se conservan como evidencia de cada revisión; no representan necesariamente el estado actual.
El backlog mantiene las prioridades y el estado por ID.

### Correcciones implementadas

- Seguridad de imagenes (#74), 2026-11-09: los tres Dockerfiles fijan `setuptools==80.10.2` en el Python global y, para training/monitoring, en el entorno virtual de runtime. El paquete oficial incluye `wheel 0.46.3` y `jaraco.context 6.1.0`, corrigiendo CVE-2026-24049 y CVE-2026-23949 en las copias de `setuptools/_vendor` que actualizar los paquetes independientes no reemplaza. Contenido del paquete verificado; pendiente reconstruccion y escaneo completo de imagenes en CI.
- CI GitOps: Poetry usa `package-mode = false` y un lock versionado; la instalacion ya no intenta instalar un paquete inexistente. El formato actual de todos los archivos `ml-platform/src` y `ml-platform/tests` pasa los comandos `flake8` y `black --check` del workflow.
- Bootstrap completo de Flux 2.7.5, APIs estables, rutas reales del repositorio y reconciliacion por capas sin doble propiedad. ArgoCD espera el application-controller como StatefulSet. El plugin `platform-kustomize` inyecta la configuracion fuera de Git y rechaza valores ficticios.
- Roles IRSA separados para Argo, MLflow, secretos de MLflow y backup. Buckets con sufijo de cuenta/region, backend bootstrap con nombre unico y publicacion inicial dev en ECR por OIDC. La activacion y el plan AWS siguen pendientes.
- Backup con cliente PostgreSQL/boto3, host correcto por overlay, ejecucion sin root, checksum y restore a una base vacia distinta. MLflow usa proxy de artefactos; en produccion usa IRSA y no las credenciales del gateway de desarrollo.
- Roles de Chaos separados, guardas de admision, canarios de datos/artefactos, predicciones con asercion y preflight AZ que bloquea PVCs y capacidad insuficiente. Los engines declaran `annotationCheck: "false"` para no depender de una anotacion ausente.
- GitHub Actions kind incluye validacion de datos, entrenamiento/gate, backup/restore, Flux/Litmus, pod-delete, cancelacion `Stop`, limpieza y evidencia retenida. Aun no se ha verificado un run verde de esta ampliacion.
- Eliminadas las imagenes inexistentes de validacion, deployment y notificacion del pipeline principal. Monitoring usa dependencias bloqueadas y una imagen versionada. El despliegue KServe requiere todavia prueba real.
- Cliente y servidor MLflow alineados en 3.17.1; hosts internos permitidos explicitamente y modelos guardados con `skops`, autorizando solo el tipo interno de arboles entrenados. El lock actualizado elimina versiones simultaneas incompatibles de SQLAlchemy y Tenacity. Una base existente requiere backup y migracion de esquema antes del upgrade.
- Feast actualizado a serializacion de claves v3. Sus pruebas usan datos recientes en almacenes temporales y verifican valores; los errores ya no se convierten en omisiones. Los snapshots SQLite antiguos necesitan rematerializacion en una base nueva antes de usarlos con la version actual.
- La etapa `test` del Dockerfile incluye `feature_store.yaml` y `feature_definitions.py`; el filtro del contexto permite ambos archivos. Sin ellos, las siete pruebas con definiciones de Feast fallaban con `FileNotFoundError`. Los datos de prueba se generan en directorios temporales.
- Arranque MLflow: un worker por pod, jobs internos desactivados, memoria reservada/limitada a 1536 MiB en dev/staging/kind y 2 GiB en produccion; cuotas ajustadas para el rollout. Un init container serializa la creacion del esquema y del experimento por defecto mediante un bloqueo PostgreSQL. Las bases existentes se validan y requieren migracion explicita si estan desactualizadas. Se conservan dos replicas en kind y probes con timeout de cinco segundos.
- Seguridad de dependencias: Pillow 13.0.0 fijado en el lock de ML y en la imagen independiente del servidor MLflow para corregir [CVE-2026-112403](https://github.com/python-pillow/Pillow/security/advisories/GHSA-8g5g-8vmr-9782). Trivy detectaba 12.3.0 en la rama del lock para Python 3.10; las ramas 3.11/3.12 ya resolvian 13.0.0. El minimo de Python sube a 3.11 porque la version corregida ya no soporta 3.10. CI e imagenes usan 3.11/3.12; training y monitoring heredan el lock actualizado.

### Evidencia en GitHub Actions

- E2E [#23 de `4494aca`](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/42413352033): entrenamiento, backup/restore y Litmus vuelven a aprobar. Serving (#52) fallo en `InferenceService declared in Git serves default-model@champion`: el InferenceService no llego a Ready en 420 s. La NetworkPolicy `model-predictors` solo permitia salida a MLflow:5000 y DNS, pero MLflow entrega URLs firmadas hacia el gateway S3 (`dev-mlflow-minio.mlflow.svc.cluster.local:9000`), asi que el predictor no podia descargar `@champion`. Se agrega salida a los pods del gateway (`app: mlflow-minio`) por 9000 en la base; la regresion cruza el endpoint que firma MLflow, el Service y pod del gateway, la salida del predictor y la entrada de MLflow en dev/staging/kind. La causa se deduce de la anotacion de la etapa, la duracion del paso y las politicas; el log del job no se reviso. Falta un nuevo E2E.
- E2E [#22 de `991bcd3`](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/42378504965): primer verde completo en kind 1.37: entrenamiento/gate, backup/restore (#54) y Litmus con pod-delete y cancelacion `Stop` (#62). El serving aun no formaba parte del workflow.
- E2E [#19 de `cb0d779`](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/40104958856): `pre-check` aprobado, confirmando acceso al API y salud de MLflow. `prepare-canary` quedo en `ImagePullBackOff`: sin configuracion de imagenes para WorkflowTemplate, los replacements de cuenta/region deformaban `mlops-platform:0.1.0`. Se agrega el transformer para las rutas Argo y una regresion del nombre ECR completo de prepare/verify en dev/staging. Produccion sigue sin workflows de Chaos. Los timeouts ahora muestran nodos pendientes y sus errores; falta nuevo E2E para validar inyeccion y cancelacion (#62).
- E2E [#18 de `47b8228`](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/40103586835): Litmus y el catalogo reconciliados; RBAC y rechazo por `chaos-mlflow-engine-scope` comprobados en el artefacto. El workflow fallo en `pre-check` y `onExit`: kubectl intento acceder a `http://localhost:8080`. Los scripts de MLflow/AZ ahora seleccionan una configuracion interna explicita con CA y `tokenFile` de la ServiceAccount montada, sin credenciales embebidas ni cambios de permisos. Los fallos del workflow muestran nodos y logs en CI. Regresiones de Chaos: 35 aprobadas; ejecucion de fallos y cancelacion aun pendientes de nuevo E2E (#62). Produccion sigue sin habilitar estos workflows.
- E2E [#17 de `0626076`](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/40102338418): entrenamiento/evaluacion/registro y backup/restore aprobados. Chaos (#62) fallo al crear el Service `litmus-chaos-exporter`: `/metrics` estaba en `metadata.labels`, donde Kubernetes no admite `/`. La configuracion `prometheus.io/*` se mueve a anotaciones en la base compartida; una regresion comprueba etiquetas y anotaciones en dev/staging/produccion. La ejecucion de experimentos y cancelacion sigue pendiente de un nuevo E2E.
- E2E [#16 de `1db9596`](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/39699942709): fallo confirmado en `evaluate-model-step` al descargar el modelo. Las URLs firmadas por MLflow apuntaban a `dev-mlflow-minio:9000`, que no resuelve desde `argo-workflows`; backup y Chaos quedaron sin ejecutar (#54/#62). `1159cc1` corrige el endpoint con DNS completo en dev/staging. La revision del 2026-10-24 extiende la correccion a la base y agrega regresion sobre el endpoint consumido por MLflow y el Service renderizado en base/dev/staging/kind. Produccion conserva su endpoint S3 de AWS. Falta una nueva ejecucion E2E verde para validar la recuperacion completa.
- [CI Pipeline #127](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/39692710670), commit `25f0683`, aprobado el 2026-10-21: Kubernetes Validate, ML Platform Tests, Terraform Validate en tres entornos, Helm Lint, MLOps Stack Validation y Security Scan. Terraform Tests contra AWS no se ejecutaron.
- La correccion de Feast de `104e203` ya esta validada en el [build de imagen de `ceb25bd`](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/39694031853), aprobado junto con su [CI Pipeline](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/39694032094).
- El [E2E de `ceb25bd`](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/39694031972) fallo en el rollout de MLflow: OOMKilled, reinicios y conflicto de creacion de tablas. La correccion de recursos e inicializacion serializada requiere una nueva ejecucion de kind antes de considerar validados backup y Chaos.
- El [E2E anterior](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/runs/39523282574), commit `f9da9d6`, tenia cliente MLflow 3.17.1 y servidor 2.22.5. El endpoint `/api/2.0/mlflow/logged-models` devolvia 404 y el entrenamiento no producia `model-uri.txt`/`run-id.txt`; backup y Chaos no llegaron a ejecutarse.

### Evidencia local

- 421 pruebas GitOps aprobadas con el lock actual, incluidas las 32 de Chaos, el bootstrap del backend, la paridad cliente/servidor MLflow y el contrato de arranque en dev/staging/produccion/kind; siete pruebas que requieren cluster excluidas por `-m "not integration"`.
- Instalacion limpia `poetry install --with test,dev` aprobada con Python 3.12 y Poetry 2.5.1; lock validado y 64 paquetes instalados compatibles. Flake8 y Black aprobados sobre los 48 archivos de `ml-platform/src/` y `ml-platform/tests/`.
- Seis pruebas nuevas del inicializador PostgreSQL aprobadas: bloqueo antes de crear tablas, validacion de bases existentes, rechazo de esquemas antiguos, timeout de bloqueo, rechazo de otros backends y mensajes sin credenciales.
- Suite ML con MLflow 3.17.1/NumPy 2: 180 pruebas aprobadas en una sola ejecucion con Python 3.12 y el conjunto de archivos copiados por la etapa Docker `test`, sin omisiones ni `xfail`. Esto verifica el contexto de pruebas; la construccion del contenedor con Python 3.11 se comprueba por separado.
- Contexto exportado con Docker: las reglas incluyen las dos definiciones Feast exactas y excluyen las bases locales. El build completo local se detuvo durante la descarga de la imagen base; no cuenta como una ejecucion aprobada de los tests en contenedor.
- 30 overlays autorizados por el AppProject; seis overlays Argo/MLflow sin placeholders; render del plugin desde un checkout sin `aws.env`; lint offline de Argo aprobado.
- MLflow 3.17.1 probado por HTTP con SQLite temporal: canario de parametro/artefacto conservado y hosts no autorizados rechazados. Las 190 dependencias instaladas pasaron la comprobacion de compatibilidad.
- Entrenamiento `src.cli step train` verificado contra un servidor HTTP MLflow 3.17.1: `POST /api/2.0/mlflow/logged-models` responde 200, ambos outputs de Argo se crean con valores validos, el modelo se recarga y predice, y el registro con alias `champion` funciona. El overlay kind renderizado usa la misma version. Esta prueba usa SQLite y almacenamiento temporal, no sustituye el E2E de Kubernetes/PostgreSQL/S3.
- Terraform dev/staging/prod validado sin backend ni llamadas de aprovisionamiento. `make test-terraform-plan` valida; no genera un plan real. Las pruebas de cluster siguen excluidas localmente.

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

- [x] Dependencias sin vulnerabilidades conocidas corregibles: Trivy (`--include-dev-deps`) bajo de 60 hallazgos en los manifiestos versionados (mas los de desarrollo) a 5, todos `GO-2026-5932` (`golang.org/x/crypto/openpgp` sin mantenimiento) en Terratest; `govulncheck` confirma que no es alcanzable y no hay version publicada con el arreglo. ml-platform: `feast` 0.67.0 (critica), `mlflow` 3.17.2 en cliente y servidor, `nltk` 3.10.4, `pyasn1` 0.6.5, `black` 26, `pytest` 9. gitops: Python minimo 3.11, cliente `kubernetes` 37 (`urllib3` 2.8.0), `requests` 2.34, `oauthlib` 4.0.1, `black` 26, `pytest` 9, `pylint` 4. Terratest: `golang.org/x/net` 0.62.0 y `go-jose` 4.1.6. Dependabot activado para Actions, pip, gomod, Terraform y Docker. 203 pruebas ML y 503 GitOps aprobadas; la prueba de Chaos lee la version de imagen de `ml-platform/pyproject.toml` en vez de fijar `0.1.0`, que el release 0.1.5 habia roto `(2026-11-08)`
- [x] Roles IAM solo en Terraform: `setup-mlops-stack.sh` ya no crea `mlops-<env>-mlflow-role` ni `mlops-<env>-kserve-role` en paralelo a `workload-identity`; antes de desplegar comprueba que existan los roles `mlflow`, `argo`, `secrets` y `backup` del entorno y se detiene si falta alguno `(2026-11-08)`
- [x] Decision 2 de serving, despliegue por alias: Git declara el InferenceService (`model-serving`, ArgoCD) y el registro decide la version. `register` devuelve la version reemplazada; `model-deployment-template` cambia la anotacion `mlops-platform/model-version`, espera `X-Model-Version` y compara predicciones; si falla, `set-alias` devuelve `@champion`, rollback verificado y workflow en fallo. Se eliminaron BuildKit, el permiso ECR push de Argo y los verbos `create/update` sobre InferenceServices. E2E en kind pendiente (#52) `(2026-11-07)`
- [x] Decision 1 de serving: `step serve` + KServe v0.21.0 `Standard` + cert-manager v1.21.3; se eliminaron 21.200 lineas de manifiestos KServe 0.11 (CRDs, webhooks, runtimes, Gateway Knative y un Secret de S3 en Git). 197 pruebas ML y 449 GitOps aprobadas localmente; E2E en kind pendiente (#52) `(2026-11-07)`
- [x] EKS 1.37 en dev/staging/prod: 1.32 estaba fuera de soporte estandar desde 2026-03-23 y AL2 no tiene AMIs para 1.33+. Nodos y GPU en AL2023, `upgrade_policy` `STANDARD`, validacion numerica >= 1.35, Cluster Autoscaler 1.37, kind 0.33.0 con nodo 1.37.0 y kubectl 1.37 en Chaos. Falta E2E en kind 1.37 y add-ons (#66/#67) `(2026-11-07)`
- [x] CI reducido a GitHub Actions: GitLab CI, CircleCI y Jenkins movidos sin cambios a `ci-cd/future/` (inactivos, sin sincronizar). Ver [`ci-cd/future/README.md`](../../ci-cd/future/README.md) `(2026-11-07)`
- [x] Chaos revisado: barrera de inicio para la sonda, downtime por tiempo real, observacion hasta completar los engines, mutex, preflight de desalojo por zona y limpieza con errores visibles. RBAC de charts limitado (HIGH-014). `(2026-10-17)` - validacion estatica y pruebas con dobles; ejecucion EKS pendiente. EC2 stop #58, particion de red desactivada #59, separacion de roles #60.
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
