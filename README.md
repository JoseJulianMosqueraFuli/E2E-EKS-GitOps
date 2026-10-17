# E2E MLOps Platform on EKS

[![CI Pipeline](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/ci.yml)
[![E2E (kind)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/e2e-kind.yml/badge.svg)](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/actions/workflows/e2e-kind.yml)

English | [Español](README.es.md)

A reference project for building an ML platform on Amazon EKS. It brings infrastructure,
model training, deployment configuration, and monitoring together in one repository.

## What it includes

- **Infrastructure as code:** Terraform modules for AWS, with dev, staging, and prod environments.
- **GitOps:** Flux manages cluster infrastructure; ArgoCD manages platform applications.
- **Training and model registry:** Argo Workflows runs training and evaluation; MLflow tracks experiments and registers approved models.
- **Serving and monitoring:** manifests for KServe, Prometheus, Grafana, and Evidently.

> **Status:** the training, evaluation, and model registration flow has passed the E2E test in
> GitHub Actions. The first full AWS deployment is still pending. See the
> [backlog](docs/project/backlog.md) for remaining work.

## Start with GitHub Actions

No local cluster is needed for these checks.

1. **Validate Terraform:** CI checks dev, staging, and prod without AWS credentials.
   Follow the [Terraform CI guide](docs/terraform-ci.md) to configure OIDC and run an initial AWS plan.
2. **Test training end to end:** run **Actions → E2E (kind) → Run workflow**.
   The [workflow](.github/workflows/e2e-kind.yml) creates its temporary cluster on the runner.
3. **Prepare an AWS deployment:** review the [pending work](docs/project/backlog.md) and
   [AWS configuration](gitops/platform/README.md). The initial plan does not deploy resources.

## Documentation

**[Read the full platform guide](docs/platform-guide.md)** for architecture, setup, commands, CI/CD, costs, and development.
The [documentation index](docs/README.md) links to the guides for each component.

| I want to… | Read |
|---|---|
| Understand the design | [Architecture](docs/architecture/implementation.md) |
| Work on models and pipelines | [ML platform guide](docs/ml-platform-guide.md) |
| Set up ArgoCD and Flux | [GitOps setup](gitops/SETUP.md) |
| Configure model monitoring | [Monitoring guide](docs/model-monitoring-guide.md) |
| Review security and costs | [Security](docs/security-best-practices.md) · [Cost estimates](docs/cost-estimation.md) |

## Contributing

See the [contribution guide](docs/contributing.md) for the development workflow and checks.
Report vulnerabilities through the [security policy](SECURITY.md).

## License

[MIT](LICENSE) · [Jose Julian Mosquera](https://github.com/JoseJulianMosqueraFuli)
