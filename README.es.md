# Plataforma MLOps E2E en EKS

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.0-blue)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-%3E%3D1.25-blue)](https://kubernetes.io/)

[English](README.md) | Español

Plataforma MLOps completa sobre Amazon EKS. Desde entrenamiento hasta producción con monitoreo incluido.

> **Nota**: ~~GitOps~~ - Integración con ArgoCD próximamente.

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
│   │Kubeflow │    │  MLflow   │        │  KServe   │    │ Grafana │ │
│   │Pipelines│    │  Registry │        │  Serving  │    │Evidently│ │
│   └─────────┘    └───────────┘        └───────────┘    └─────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                    Amazon EKS (Terraform)                           │
│         VPC │ EKS │ S3 │ ECR │ Glue │ KMS │ IAM                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Qué obtienes

| Componente               | Propósito                                            |
| ------------------------ | ---------------------------------------------------- |
| **Módulos Terraform**    | VPC, EKS, S3, ECR, Glue - reutilizables y testeados  |
| **Plataforma ML**        | Modelos listos para usar, pipelines de training, CLI |
| **MLflow**               | Trackear experimentos, registrar modelos             |
| **Kubeflow**             | Orquestar workflows de ML                            |
| **KServe**               | Servir modelos con autoscaling                       |
| **Prometheus + Grafana** | Métricas y dashboards                                |
| **Evidently**            | Detectar data drift automáticamente                  |
| **Multi-ambiente**       | Configs para dev, staging, prod                      |
| **Templates CI/CD**      | GitHub Actions, GitLab, CircleCI, Jenkins            |

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
python >= 3.9
go >= 1.21
make

# Configurar AWS
aws configure
```

## Dependencias Clave

| Paquete            | Versión | Notas                                          |
| ------------------ | ------- | ---------------------------------------------- |
| MLflow             | 3.5.0   | Tracking de experimentos y registro de modelos |
| Apache Airflow     | 3.1.6   | Orquestación de workflows                      |
| Feast              | 0.54.0  | Feature store                                  |
| Prefect            | 2.20.17 | Pipelines de datos                             |
| KServe             | 0.11.0  | Serving de modelos                             |
| Kubeflow Pipelines | 2.0.1   | Pipelines de ML                                |

> **Nota de Seguridad**: Todas las dependencias se actualizan regularmente para corregir CVEs. Ver `ml-platform/requirements.txt` para versiones actuales.

## Inicio Rápido

### Opción A: Plataforma ML Local (sin cloud)

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps/ml-platform

pip install -r requirements.txt

# Crear datos de ejemplo y entrenar
python src/main.py create-sample data/sample.csv --n-samples 1000
python src/main.py train data/sample.csv

# Ejecutar inferencia
python src/main.py inference data/sample.csv \
    --model-path artifacts/model_*.joblib \
    --output-path predictions.json
```

### Opción B: Despliegue Completo en AWS

```bash
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# 1. Desplegar infraestructura
make init ENV=dev
make plan ENV=dev
make apply ENV=dev

# 2. Configurar kubectl
aws eks update-kubeconfig --name mlops-dev-cluster --region us-west-2

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
│   └── mlops-stack/          # MLflow, Kubeflow, KServe, monitoreo
├── ml-platform/              # Código ML y pipelines
│   └── src/                  # Modelos, procesamiento de datos, CLI
├── ci-cd/                    # Configuraciones CI/CD
├── scripts/                  # Scripts de automatización
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
python src/main.py train data/dataset.csv

# Inferencia
python src/main.py inference data/input.csv --model-path artifacts/model.joblib

# Validar datos
python src/main.py validate data/production.csv --create-suite
```

### Acceder a Servicios

```bash
make port-forward-mlflow    # MLflow UI en localhost:5000
make port-forward-grafana   # Grafana en localhost:3000
make port-forward-kubeflow  # Kubeflow en localhost:8080
```

## Documentación

| Documento                                              | Descripción                         |
| ------------------------------------------------------ | ----------------------------------- |
| [Guía de Inicio Rápido](docs/quick-start-guide.md)     | Configuración paso a paso           |
| [Guía de Plataforma ML](docs/ml-platform-guide.md)     | Detalles de la plataforma ML        |
| [Monitoreo de Modelos](docs/model-monitoring-guide.md) | Configuración de detección de drift |
| [Seguridad](docs/security-best-practices.md)           | Guías de seguridad                  |

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

# Instalar dependencias de desarrollo
cd ml-platform && pip install -r requirements-dev.txt

# Ejecutar tests
make test
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
