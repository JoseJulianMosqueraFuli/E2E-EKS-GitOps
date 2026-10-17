# Plataforma MLOps E2E en EKS

[![CI Pipeline](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml)
[![E2E (kind)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/e2e-kind.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/e2e-kind.yml)

[English](README.md) | Español

Proyecto de referencia para construir una plataforma de machine learning en Amazon EKS.
Reúne infraestructura, entrenamiento de modelos, configuración de despliegue y monitoreo en un repositorio.

## Qué incluye

- **Infraestructura como código:** módulos Terraform para AWS, con entornos dev, staging y prod.
- **GitOps:** Flux gestiona la infraestructura del clúster; ArgoCD gestiona las aplicaciones de la plataforma.
- **Entrenamiento y registro de modelos:** Argo Workflows ejecuta el entrenamiento y la evaluación; MLflow registra experimentos y modelos aprobados.
- **Servicio de modelos y monitoreo:** manifiestos para KServe, Prometheus, Grafana y Evidently.

> **Estado:** el flujo de entrenamiento, evaluación y registro de modelos pasó la prueba E2E en
> GitHub Actions. El primer despliegue completo en AWS sigue pendiente. Consulta el
> [backlog](docs/project/backlog.md) para ver el trabajo restante.

## Empieza con GitHub Actions

Estas comprobaciones no necesitan un clúster local.

1. **Valida Terraform:** CI comprueba dev, staging y prod sin credenciales de AWS.
   Sigue la [guía de Terraform en CI](docs/terraform-ci.md) para configurar OIDC y ejecutar un plan inicial en AWS.
2. **Prueba el entrenamiento completo:** ejecuta **Actions → E2E (kind) → Run workflow**.
   El [workflow](.github/workflows/e2e-kind.yml) crea su clúster temporal en el runner.
3. **Prepara el despliegue en AWS:** revisa los [pendientes](docs/project/backlog.md) y la
   [configuración de AWS](gitops/platform/README.md). El plan inicial no despliega recursos.

## Documentación

**[Lee la guía completa de la plataforma](docs/platform-guide.es.md)**: arquitectura, instalación, comandos, CI/CD, costos y desarrollo.
El [índice de documentación](docs/README.md) enlaza las guías de cada componente.

| Quiero… | Consultar |
|---|---|
| Entender el diseño | [Arquitectura](docs/architecture/implementation.md) |
| Trabajar con modelos y pipelines | [Guía de la plataforma ML](docs/ml-platform-guide.md) |
| Configurar ArgoCD y Flux | [Instalación de GitOps](gitops/SETUP.md) |
| Configurar el monitoreo de modelos | [Guía de monitoreo](docs/model-monitoring-guide.md) |
| Revisar seguridad y costos | [Seguridad](docs/security-best-practices.md) · [Estimación de costos](docs/cost-estimation.md) |

## Contribuir

Consulta la [guía de contribución](docs/contributing.md) para conocer el flujo de desarrollo y las comprobaciones.
Reporta vulnerabilidades mediante la [política de seguridad](SECURITY.md).

## Licencia

[MIT](LICENSE) · [Jose Julian Mosquera](https://github.com/JoseJulianMosqueraFuli)
