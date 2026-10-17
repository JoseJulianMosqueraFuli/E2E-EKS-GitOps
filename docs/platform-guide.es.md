# Guía completa de la plataforma

Arquitectura, componentes, preparación, referencia de comandos, workflows y estimaciones operativas de la plataforma MLOps en EKS.

[Resumen del proyecto](../README.es.md) · [Índice de documentación](README.md) · [English](platform-guide.md)

El flujo de entrenamiento, evaluación y registro pasó la prueba E2E en kind dentro de GitHub Actions.
El primer despliegue completo en AWS sigue pendiente. Revisa el [backlog](project/backlog.md) antes de desplegar.
Empieza desde GitHub Actions; la preparación de Python descrita abajo es opcional y no requiere un clúster local.

## Tabla de Contenidos

- [Qué es esto?](#qué-es-esto)
- [Qué obtienes](#qué-obtienes)
- [Requisitos](#requisitos)
- [Dependencias Clave](#dependencias-clave)
- [Inicio Rápido](#inicio-rápido)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Uso](#uso)
- [Documentación](#documentación)
- [Estimados de Tiempo y Costo de Despliegue](#estimados-de-tiempo-y-costo-de-despliegue)
- [Resiliencia y Chaos Engineering](#resiliencia-y-chaos-engineering)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

## Qué es esto?

La plataforma conecta las siguientes etapas del ciclo de vida de ML en Kubernetes:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Tu Workflow de ML                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Entrenar ──► Registrar en MLflow ──► Deploy en KServe ──► Monitorear
│       │                │                     │                 │    │
│       ▼                ▼                     ▼                 ▼    │
│   ┌─────────┐    ┌───────────┐        ┌───────────┐    ┌─────────┐ │
│   │  Argo   │    │  MLflow   │        │  KServe   │    │ Grafana │ │
│   │Workflows│    │  Registry │        │  Serving  │    │Evidently│ │
│   └─────────┘    └───────────┘        └───────────┘    └─────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                    Amazon EKS (Terraform)                           │
│         VPC │ EKS │ S3 │ ECR │ Glue │ KMS │ IAM                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Qué obtienes

| Componente                | Propósito                                            |
| ------------------------- | ---------------------------------------------------- |
| **Módulos Terraform**     | VPC, EKS, S3, ECR, Glue - reutilizables y testeados  |
| **Plataforma ML**         | Modelos listos para usar, pipelines de training, CLI |
| **Imagen `mlops-platform`** | Una sola imagen para todos los pasos del pipeline (`step split/train/evaluate/register`) |
| **Argo Workflows v4**     | Pipeline de entrenamiento con gate de promoción contra el modelo `@champion` |
| **MLflow 2.22**           | Experimentos y registro de modelos con aliases (imagen propia con drivers de PostgreSQL y S3) |
| **Kubeflow Pipelines**    | UI/SDK de pipelines opcional (KFP 2.17.2)            |
| **KServe**                | Servir modelos con autoscaling                       |
| **Prometheus + Grafana**  | Métricas, dashboards y monitoreo de costos           |
| **Evidently**             | Detectar data drift automáticamente                  |
| **NVIDIA GPU (opcional)** | Node groups GPU + GPU Operator para workloads CUDA   |
| **Istio mTLS**            | Políticas mTLS; las brechas de cobertura están en el backlog   |
| **Gatekeeper/OPA**        | Políticas de seguridad en admisión del cluster       |
| **Multi-ambiente**        | Configs para dev, staging, prod                      |
| **Templates CI/CD**       | GitHub Actions, GitLab, CircleCI, Jenkins            |
| **Prueba E2E**            | Argo + MLflow + entrenamiento en kind, solo en GitHub Actions |
| **Reglas para agentes IA** | Instrucciones compartidas en `AGENTS.md` y `.agents/`; entradas mínimas por herramienta |

## Requisitos

| Tarea | Requisitos |
|---|---|
| Explorar el proyecto y ejecutar CI | Acceso a GitHub; el runner instala las herramientas necesarias |
| Generar un plan inicial en AWS | Environment de GitHub, rol OIDC de planificación, `AWS_PLAN_ROLE_ARN` y `AWS_REGION`; ver [Terraform en CI](terraform-ci.md) |
| Trabajar con Python (opcional) | Git, Python 3.10–3.12 y Poetry; instalar las dependencias del componente |
| Operar un entorno AWS existente | AWS CLI v2, sesión AWS autorizada, Terraform, kubectl, Kustomize, Helm y Make en el equipo de ejecución |
| Ejecutar pruebas de integración de infraestructura | Go 1.21 y acceso a AWS; Terratest crea recursos reales |

Las raíces Terraform declaran `>= 1.0`; el [workflow de CI](../.github/workflows/ci.yml) fija su propia versión.
Para reproducir CI, usa las versiones de sus workflows y archivos de dependencias.
Configura la autenticación AWS del equipo de ejecución mediante tu perfil o sesión autorizada;
`aws configure` es el punto de configuración de la CLI. GitHub Actions usa OIDC en lugar de claves almacenadas.

## Dependencias Clave

| Paquete            | Versión     | Notas                                                      |
| ------------------ | ----------- | ---------------------------------------------------------- |
| MLflow             | 2.22.x      | Misma versión en el cliente (`poetry.lock`) y en la imagen del servidor |
| scikit-learn       | >= 1.3      | Entrenamiento (preprocesamiento + modelo guardados como un solo pipeline) |
| pandas / pyarrow   | 2.x / >= 14 | CSV y Parquet, rutas locales o `s3://`                     |
| Great Expectations | 1.x         | Extra opcional `validation`                                |
| Evidently          | 0.7.x       | Extra opcional `monitoring`                                |
| Feast              | 0.40.x      | Extra opcional `features`                                  |
| Argo Workflows     | v4.0.13     | Orquestación del pipeline                                  |
| Kubeflow Pipelines | 2.17.2      | Opcional                                                   |

> Lista completa de dependencias y extras en [`ml-platform/pyproject.toml`](../ml-platform/pyproject.toml). `poetry install -E dev` instala
> todo lo necesario para los tests; la imagen de contenedor instala solo las dependencias core.

## Inicio Rápido

### Empieza aquí: GitHub Actions

1. Sube una rama o abre un pull request para ejecutar las comprobaciones correspondientes de **CI Pipeline**.
   La validación Terraform cubre dev, staging y prod sin credenciales de AWS.
2. Sigue la [configuración de Terraform en CI](terraform-ci.md) para preparar el rol y las variables del environment.
   Ejecuta **Actions → Terraform Initial Plan → Run workflow** desde `main`, empezando por `dev`.
   El plan parte de un estado temporal vacío: no despliega recursos ni compara infraestructura existente.
3. Ejecuta **Actions → E2E (kind) → Run workflow** para construir las imágenes y comprobar entrenamiento,
   evaluación, registro y rechazo de un candidato que no supera el criterio de promoción.
   El clúster temporal se crea en el runner de GitHub.

Estos workflows son el camino inicial de validación. El despliegue en AWS sigue siendo un hito aparte y pendiente.

### Opción A: Desarrollo Python (opcional, sin clúster local)

Ejecuta estos comandos en un equipo de desarrollo con recursos suficientes. Asigna a `TRAINING_RUN_ID`
el ID mostrado por el entrenamiento antes de usar el ejemplo de inferencia. Usa datos sin la columna
objetivo para inferencia; la [guía ML](ml-platform-guide.md) explica la preparación y configuración.

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps/ml-platform

# Instalar con Poetry (recomendado)
pip install poetry
poetry install -E dev

# Crear datos de ejemplo y entrenar
poetry run python -m src.cli create-sample data/sample.csv --n-samples 1000
poetry run python -m src.cli train data/sample.csv
poetry run python -c 'import pandas as pd; pd.read_csv("data/sample.csv").drop(columns=["target"]).to_csv("data/input.csv", index=False)'

# Ejecutar inferencia
poetry run python -m src.cli inference data/input.csv \
    --model-path "artifacts/model_${TRAINING_RUN_ID}.joblib" \
    --output-path predictions.json
```

### Opción B: Despliegue Completo en AWS

Esta es la referencia operativa para un equipo de ejecución configurado o un futuro runner de despliegue.
El workflow de planes iniciales no realiza estos pasos. Antes de usarlos, resuelve los
[bloqueos de despliegue](project/backlog.md): backend (HIGH-001), inyección de configuración en ArgoCD
(#48), IRSA de workloads (#50), nombres únicos de buckets (#51), imágenes faltantes (#52) y publicación en ECR (#55).
Instala/configura Flux y ArgoCD siguiendo la [guía de GitOps](../gitops/SETUP.md).
Cada recurso debe tener un único gestor; evita instalar la misma aplicación mediante Helm y ArgoCD.

La cuenta y la región salen de `gitops/platform/aws.env` (fuera de git; se copia desde `aws.env.example`, ver
[`gitops/platform/README.md`](../gitops/platform/README.md)). Antes del primer `apply`:

1. Inicializar el backend de Terraform una vez por ambiente: `./scripts/bootstrap-terraform-backend.sh dev "${AWS_REGION}"`
   (ver HIGH-001 en [`docs/project/critical.md`](project/critical.md)).
2. Los nombres de buckets S3 son globales: confirmar que los nombres usados por Terraform y los manifiestos estén libres.
3. Las imágenes se referencian desde ECR (`mlops-<env>-trainer`, `mlops-<env>-mlflow-server`); publicarlas
   desde CI necesita un rol OIDC (pendiente, ver [`docs/project/backlog.md`](project/backlog.md)).

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# 1. Desplegar infraestructura
make init ENV=dev
make plan ENV=dev
make apply ENV=dev

# 2. Configurar kubectl
aws eks update-kubeconfig --name mlops-dev-cluster --region "${AWS_REGION}"

# 3. Instalar stack MLOps
make mlops-core    # MLflow + Monitoreo
# o
make mlops-full    # MLflow + Kubeflow + Monitoreo

# 4. Acceder a servicios
make port-forward-mlflow   # http://localhost:5000
make port-forward-grafana  # http://localhost:3000
```

## Estructura del Proyecto

Los manifiestos canónicos de cada aplicación están en `gitops/applications/apps/<app>/base/`, con sus
overlays en `overlays/{dev,staging,production}/`. Terraform usa `infra/environments/{dev,staging,prod}/`.
La [arquitectura detallada](architecture/implementation.md) explica las responsabilidades de Terraform, Flux y ArgoCD.

```
.
├── infra/                    # Infraestructura Terraform
│   ├── modules/              # Módulos reutilizables (vpc, eks, s3, ecr, glue)
│   └── environments/         # Configs por ambiente (dev, staging, prod)
├── k8s/                      # Manifiestos Kubernetes
│   ├── mlops-stack/          # MLflow, KServe, monitoreo (overlays)
│   └── security/             # Istio mTLS, políticas Gatekeeper
├── gitops/                   # Fuente de verdad GitOps (ArgoCD + Flux)
│   ├── applications/         # Aplicaciones ArgoCD
│   │   ├── apps/             # mlflow, kubeflow, kserve, monitoring, gpu-operator
│   │   ├── environments/     # Overlays por ambiente (dev/staging/production)
│   │   └── projects/         # Proyectos ArgoCD + ApplicationSet
│   ├── charts/               # Helm charts (mlflow, kserve, kubeflow-pipelines, monitoring-stack)
│   ├── infrastructure/       # Infraestructura del cluster gestionada por Flux
│   │   ├── addons/           # Addons EKS (ALB, EBS CSI, Autoscaler)
│   │   ├── clusters/         # Bootstrap por cluster
│   │   ├── controllers/      # Controladores Flux + ArgoCD
│   │   ├── networking/       # Ingress, Istio, Network Policies
│   │   ├── security/         # RBAC, IRSA, Pod Security
│   │   └── sources/          # Fuentes Git y Helm
│   ├── scripts/              # Automatización (install, promote, validate)
│   └── tests/                # Tests property-based (Hypothesis)
├── ml-platform/              # Código ML y pipelines
│   ├── src/                  # Modelos, procesamiento de datos, CLI (incluye comandos `step`)
│   ├── tests/                # Tests unitarios e integración
│   ├── Dockerfile            # Imagen `mlops-platform` (etapas builder / test / runtime)
│   ├── Dockerfile.mlflow-server  # Servidor MLflow con drivers de PostgreSQL y S3
│   └── pyproject.toml        # Paquete Python con extras opcionales
├── ci-cd/                    # Configuraciones CI/CD (Jenkins)
├── scripts/                  # Scripts de automatización
│   └── e2e/                  # Prueba de humo en kind (corre en GitHub Actions)
├── .github/workflows/        # CI, build de imagen, E2E en kind, promoción entre ambientes
├── .agents/                  # Reglas y servidores MCP para agentes IA (fuente de verdad)
└── docs/                     # Documentación
    ├── architecture/         # Arquitectura de la plataforma
    ├── project/              # Pendientes y hallazgos críticos
    ├── reports/              # Reportes históricos
    └── proposals/            # Propuestas de evolución
```

## Uso

### Infraestructura

| Comando                | Descripción              |
| ---------------------- | ------------------------ |
| `make init ENV=dev`    | Inicializar Terraform    |
| `make plan ENV=dev`    | Ver cambios planificados |
| `make apply ENV=dev`   | Aplicar cambios          |
| `make destroy ENV=dev` | Destruir infraestructura |

### Stack MLOps

| Comando                | Descripción                 |
| ---------------------- | --------------------------- |
| `make mlops-core`      | Instalar MLflow + Monitoreo |
| `make mlops-full`      | Instalar MLflow + Kubeflow + Monitoreo |
| `make mlops-install MLOPS_TOOLS=mlflow,kubeflow,kserve,monitoring` | Seleccionar herramientas explícitamente, incluyendo KServe |
| `make mlops-status`    | Ver estado                  |
| `make mlops-uninstall` | Desinstalar stack           |

### CLI de la Plataforma ML

```bash
# Entrenar
poetry run python -m src.cli train data/dataset.csv

# Inferencia
poetry run python -m src.cli inference data/input.csv --model-path artifacts/model.joblib

# Validar datos (necesita el extra `validation`)
poetry run python -m src.cli validate data/production.csv --create-suite

# Pasos del pipeline (lo que ejecuta cada tarea de Argo dentro de la imagen `mlops-platform`)
poetry run python -m src.cli step split    --input data/sample.csv --output data/run --outputs-dir out
poetry run python -m src.cli step train    --features data/run/train.parquet --model-name clf --experiment-name dev --outputs-dir out
poetry run python -m src.cli step evaluate --model-uri "$(cat out/model-uri.txt)" --test-data data/run/test.parquet --model-name clf --outputs-dir out
[ "$(cat out/model-approved.txt)" = "true" ] && \
poetry run python -m src.cli step register --model-uri "$(cat out/model-uri.txt)" --model-name clf --outputs-dir out
```

Los ejemplos anteriores se ejecutan desde `ml-platform/`. `step split` escribe los datasets de
entrenamiento y prueba; `step train` registra el candidato y guarda su URI en `out/model-uri.txt`.
La evaluación escribe su decisión en `out/model-approved.txt`; el registro debe respetarla.
La plantilla Argo aplica esa condición. El comando individual `register` no sustituye las comprobaciones de la orquestación.

`step evaluate` aprueba un candidato solo si alcanza `--min-score` y supera al modelo con el alias
`@champion` por `--min-improvement`; `step register` asigna ese alias a la nueva versión.

### Workflows de CI

| Workflow                    | Qué hace                                                               |
| --------------------------- | ---------------------------------------------------------------------- |
| [ci.yml](../.github/workflows/ci.yml)                    | Validación de Terraform para dev/staging/prod, Kubernetes, Python y Helm + seguridad |
| [terraform-plan.yml](../.github/workflows/terraform-plan.yml)        | Planes iniciales AWS manuales mediante OIDC de lectura; sin apply |
| [ml-platform-image.yml](../.github/workflows/ml-platform-image.yml)     | Tests dentro de la imagen; publica `mlops-platform` en GHCR (amd64, tags `sha-`) |
| [e2e-kind.yml](../.github/workflows/e2e-kind.yml)              | Construye las dos imágenes, crea kind y ejecuta `scripts/e2e/kind-smoke.sh` |
| [environment-promotion.yml](../.github/workflows/environment-promotion.yml) | Promueve cambios entre ambientes                                       |

Consulta [Terraform en CI](terraform-ci.md) para OIDC, permisos, referencias de facturación y los
límites de un plan con estado vacío. La planificación Terraform se ejecuta íntegramente en GitHub Actions.

### Acceder a Servicios

```bash
make port-forward-mlflow    # MLflow UI en localhost:5000
make port-forward-grafana   # Grafana en localhost:3000
make port-forward-kubeflow  # Kubeflow en localhost:8080
```

## Documentación

> **Índice completo: [Centro de documentación](README.md)** — arquitectura, pendientes, reportes, propuestas y guías.

| Documento                                                             | Descripción                           |
| --------------------------------------------------------------------- | ------------------------------------- |
| [Guía de Inicio Rápido](quick-start-guide.md)                    | Configuración paso a paso             |
| [Guía de Plataforma ML](ml-platform-guide.md)                    | Detalles de la plataforma ML          |
| [Monitoreo de Modelos](model-monitoring-guide.md)                | Configuración de detección de drift   |
| [Seguridad](security-best-practices.md)                          | Guías de seguridad (mTLS, Gatekeeper) |
| [GPU Operator Setup](../gitops/applications/apps/gpu-operator/README.md) | NVIDIA GPU opcional en EKS            |

## Estimados de Tiempo y Costo de Despliegue

Las cifras siguientes conservan los supuestos de planificación del README anterior; no son una
cotización vigente verificada ni tiempos medidos de despliegue. El desglose ampliado, con nodos GPU y
múltiples entornos, está en la [estimación de costos](cost-estimation.md).

### Supuestos de costos AWS del README anterior

| Recurso | Costo/Hora |
|---------|------------|
| EKS Control Plane | $0.10 |
| NAT Gateway | $0.045 + datos |
| EC2 t3.medium (x2 nodos, default de dev) | $0.0416 c/u |

**Estimación de trabajo anterior para una ejecución E2E de 3 horas: ~$1–$2 USD**, más EBS, balanceadores y transferencia de datos. Recalcula según `AWS_REGION`, la cantidad real de nodos y los tipos de instancia antes de asignar presupuesto.

> En un entorno de pruebas desechable, prepara y revisa la limpieza con `make destroy ENV=dev` después de recoger resultados y preservar los datos necesarios. Destruye los recursos gestionados por ese entorno; no es una comprobación rutinaria.

### Estimados de Tiempo

| Fase | Duracion |
|------|----------|
| `terraform apply` (infraestructura) | 15-25 min |
| Deploy stack MLOps (ArgoCD sync) | 10-15 min |
| Validacion completa y tests | 10-15 min |
| `terraform destroy` (limpieza) | 10-15 min |
| **Total end-to-end** | **~1 hora** |

## Resiliencia y Chaos Engineering

Litmus proporciona experimentos de eliminación de pods, estrés de recursos, drenaje de nodos y desalojo por zona.
El primer objetivo es MLflow en dev: comprobar disponibilidad, iniciar una sonda, eliminar un pod,
comprobar el resultado y la recuperación, y registrar una nueva ejecución de MLflow.

El workflow de zona usa taints para desalojar pods; no reproduce la pérdida de red o almacenamiento de AWS.
La partición de red permanece detenida hasta demostrar el aislamiento (#59). Los permisos efectivos
y la recuperación tras abortos aún necesitan validación en EKS (#60).

El [runbook de Chaos](../gitops/applications/apps/chaos/README.md) contiene requisitos, comandos,
criterios de éxito y limpieza. El [plan de adopción](chaos-engineering-proposal.md) desarrolla las fases siguientes.

## Contribuir

Sigue la [guía de contribución](contributing.md) y usa GitHub Actions para las comprobaciones correspondientes.
Los comandos opcionales de desarrollo de abajo conservan la referencia completa. `make test` ejecuta Terratest:
usa AWS real y se reserva para pruebas de infraestructura planificadas, no para una contribución ordinaria.

### Cómo Contribuir

1. Haz fork del repositorio
2. Crea tu rama: `git checkout -b feature/mi-feature`
3. Realiza tus cambios
4. Revisa las comprobaciones de GitHub Actions; opcionalmente, `make validate-all` en el equipo de desarrollo
5. Commit: `git commit -m 'feat(ml): add model support'`
6. Push: `git push origin feature/mi-feature`
7. Abre un Pull Request

### Configuración de Desarrollo

```bash
# Clonar tu fork
git clone https://github.com/TU_USUARIO/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# Instalar dependencias de desarrollo con Poetry
cd ml-platform
pip install poetry
poetry install -E dev

# Ejecutar tests
poetry run pytest tests/ -v
```

### Estilo de Código

- Terraform: Usar `terraform fmt`
- Python: Seguir PEP 8
- Kubernetes: Usar `kubectl apply --dry-run=client`

### Reportar Issues

- Usar GitHub Issues
- Incluir pasos para reproducir
- Agregar logs o screenshots relevantes

## Licencia

Este proyecto está bajo la Licencia MIT - ver [LICENSE](../LICENSE) para detalles.

---

Construido por [Jose Julian Mosquera](https://github.com/JoseJulianMosqueraFuli)

_Última actualización: 2026-10-17_
