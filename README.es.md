# Plataforma MLOps E2E en EKS

[![CI Pipeline](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml)
[![E2E (kind)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/e2e-kind.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/e2e-kind.yml)
[![ML Platform Image](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ml-platform-image.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ml-platform-image.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.0-blue)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-%3E%3D1.32-blue)](https://kubernetes.io/)

[English](README.md) | Español

Plataforma MLOps completa sobre Amazon EKS. Desde entrenamiento hasta producción con monitoreo incluido.

> **Estado (octubre 2026)**: los manifiestos GitOps están completos y validados estáticamente. El camino de
> entrenamiento (Argo Workflows → MLflow → registro de modelos con gate de promoción) se prueba de punta a
> punta en kind dentro de CI (`.github/workflows/e2e-kind.yml`). El siguiente hito es el primer despliegue
> completo en AWS (`us-east-1`). El trabajo pendiente está en [`backlog.md`](backlog.md).

## Qué es esto?

Un setup completo para correr workloads de ML en Kubernetes:

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
| **Istio mTLS**            | TLS mutuo estricto entre todos los servicios MLOps   |
| **Gatekeeper/OPA**        | Políticas de seguridad en admisión del cluster       |
| **Multi-ambiente**        | Configs para dev, staging, prod                      |
| **Templates CI/CD**       | GitHub Actions, GitLab, CircleCI, Jenkins            |
| **Prueba E2E**            | Argo + MLflow + entrenamiento en kind, solo en GitHub Actions |
| **Reglas para agentes IA** | Reglas compartidas + MCP de solo lectura para Kiro, VS Code y Claude Code (`.agents/`) |

## Tabla de Contenidos

- [Requisitos](#requisitos)
- [Inicio Rápido](#inicio-rápido)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Uso](#uso)
- [Documentación](#documentación)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

## Requisitos

```bash
# Herramientas necesarias
terraform >= 1.0
kubectl >= 1.25
helm >= 3.0
aws-cli >= 2.0
python >= 3.10
go >= 1.21
make

# Configurar AWS
aws configure
```

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

> Lista completa de dependencias y extras en `ml-platform/pyproject.toml`. `poetry install -E dev` instala
> todo lo necesario para los tests; la imagen de contenedor instala solo las dependencias core.

## Inicio Rápido

### Opción A: Plataforma ML Local (sin cloud)

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps/ml-platform

# Instalar con Poetry (recomendado)
pip install poetry
poetry install -E dev

# Crear datos de ejemplo y entrenar
poetry run python -m src.cli create-sample data/sample.csv --n-samples 1000
poetry run python -m src.cli train data/sample.csv

# Ejecutar inferencia
poetry run python -m src.cli inference data/sample.csv \
    --model-path artifacts/model_*.joblib \
    --output-path predictions.json
```

### Opción B: Despliegue Completo en AWS

La cuenta y la región salen de `gitops/platform/aws.env` (fuera de git; se copia desde `aws.env.example`, ver
[`gitops/platform/README.md`](gitops/platform/README.md)). Región por defecto: `us-east-1`. Antes del primer `apply`:

1. Inicializar el backend de Terraform una vez por ambiente: `./scripts/bootstrap-terraform-backend.sh dev us-east-1`
   (ver HIGH-001 en [`critical.md`](critical.md)).
2. Los nombres de buckets S3 son globales: confirmar que los nombres usados por Terraform y los manifiestos estén libres.
3. Las imágenes se referencian desde ECR (`mlops-<env>-trainer`, `mlops-<env>-mlflow-server`); publicarlas
   desde CI necesita un rol OIDC (pendiente, ver [`backlog.md`](backlog.md)).

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# 1. Desplegar infraestructura
make init ENV=dev
make plan ENV=dev
make apply ENV=dev

# 2. Configurar kubectl
aws eks update-kubeconfig --name mlops-dev-cluster --region us-east-1

# 3. Instalar stack MLOps
make mlops-core    # MLflow + Monitoreo
# o
make mlops-full    # Stack completo (MLflow + Kubeflow + KServe + Monitoreo)

# 4. Acceder a servicios
make port-forward-mlflow   # http://localhost:5000
make port-forward-grafana  # http://localhost:3000
```

## Estructura del Proyecto

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
| `make mlops-full`      | Instalar stack completo     |
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
poetry run python -m src.cli step register --model-uri "$(cat out/model-uri.txt)" --model-name clf --outputs-dir out
```

`step evaluate` aprueba un candidato solo si alcanza `--min-score` y supera al modelo con el alias
`@champion` por `--min-improvement`; `step register` asigna ese alias a la nueva versión.

### Workflows de CI

| Workflow                    | Qué hace                                                               |
| --------------------------- | ---------------------------------------------------------------------- |
| `ci.yml`                    | Validación de Terraform, Kubernetes, Python y Helm + escaneo de seguridad |
| `ml-platform-image.yml`     | Tests dentro de la imagen; publica `mlops-platform` en GHCR (amd64, tags `sha-`) |
| `e2e-kind.yml`              | Construye las dos imágenes, crea kind y ejecuta `scripts/e2e/kind-smoke.sh` |
| `environment-promotion.yml` | Promueve cambios entre ambientes                                       |

Los runners de GitHub son gratuitos para repositorios públicos, así que estos workflows no tienen costo.

### Acceder a Servicios

```bash
make port-forward-mlflow    # MLflow UI en localhost:5000
make port-forward-grafana   # Grafana en localhost:3000
make port-forward-kubeflow  # Kubeflow en localhost:8080
```

## Documentación

| Documento                                                             | Descripción                           |
| --------------------------------------------------------------------- | ------------------------------------- |
| [Guía de Inicio Rápido](docs/quick-start-guide.md)                    | Configuración paso a paso             |
| [Guía de Plataforma ML](docs/ml-platform-guide.md)                    | Detalles de la plataforma ML          |
| [Monitoreo de Modelos](docs/model-monitoring-guide.md)                | Configuración de detección de drift   |
| [Seguridad](docs/security-best-practices.md)                          | Guías de seguridad (mTLS, Gatekeeper) |
| [GPU Operator Setup](gitops/applications/apps/gpu-operator/README.md) | NVIDIA GPU opcional en EKS            |

## Estimados de Tiempo y Costo de Despliegue

Ejecutar el test E2E completo en AWS genera costos reales. Esto es lo que puedes esperar:

### Costos AWS (estimado para una ejecucion E2E)

| Recurso | Costo/Hora |
|---------|------------|
| EKS Control Plane | $0.10 |
| NAT Gateway | $0.045 + datos |
| EC2 t3.medium (x2 nodos, default de dev) | $0.0416 c/u |

**Total para un test E2E de 3 horas en `us-east-1`: ~$1 - $2 USD** (más EBS, load balancers y
transferencia de datos). Precios on-demand; verificar los precios actuales de AWS antes de ejecutar.

> Tip: Siempre ejecuta `make destroy ENV=dev` inmediatamente despues de testear para evitar cargos continuos.

### Estimados de Tiempo

| Fase | Duracion |
|------|----------|
| `terraform apply` (infraestructura) | 15-25 min |
| Deploy stack MLOps (ArgoCD sync) | 10-15 min |
| Validacion completa y tests | 10-15 min |
| `terraform destroy` (limpieza) | 10-15 min |
| **Total end-to-end** | **~1 hora** |

## Contribuir

Las contribuciones son bienvenidas. Por favor lee las siguientes guías.

### Cómo Contribuir

1. Haz fork del repositorio
2. Crea tu rama: `git checkout -b feature/mi-feature`
3. Realiza tus cambios
4. Ejecuta tests: `make validate-all && make test`
5. Commit: `git commit -m 'Agregar mi feature'`
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

Este proyecto está bajo la Licencia MIT - ver [LICENSE](LICENSE) para detalles.

---

Construido por [Jose Julian Mosquera](https://github.com/JoseJulianMosqueraFuli)

_Última actualización: 2026-10-10_
