---
description: Terraform best practices for infra modules and environments
globs: **/*.tf, **/*.tfvars.example, infra/**
---

# Terraform

## Structure

- Reusable logic lives in `infra/modules/<name>/` with `main.tf`, `variables.tf`, `outputs.tf` (add `versions.tf` / `locals.tf` when they grow). Environment roots in `infra/environments/<env>/` only compose modules and set variables.
- Modules must not configure providers or backends; roots do.
- One concern per module. Do not create resources of another module's domain (e.g. IAM roles for EKS workloads belong with the workload/IRSA definition, not the VPC module).

## Code style

- `terraform fmt -recursive` before every commit. snake_case names; resource names describe the role, not the type (`aws_s3_bucket.artifacts`, not `aws_s3_bucket.bucket`).
- Every variable has `type` and `description`; add `validation` blocks for constrained inputs (CIDRs, env names, instance types). Mark secrets `sensitive = true`.
- Every output has a `description`. Output IDs/ARNs that downstream layers (GitOps, IRSA) consume.
- Use `for_each` over `count` for collections of named things. Use `count` only for on/off toggles.
- Prefer `locals` for derived names and tags (`name_prefix`, `common_tags`); apply `default_tags` in the provider.
- Avoid `depends_on` unless a hidden dependency truly exists. Never use `local-exec`/`null_resource` for things a provider can manage.

## Versions

- Pin providers with pessimistic constraints (`~> 5.0`) and commit `.terraform.lock.hcl` once the backend is active.
- Pin community modules to an exact version.
- Keep `required_version` aligned across environments.

## State and safety

- Backend is local by design until HIGH-001 is resolved; do not uncomment the S3 backend without running `scripts/bootstrap-terraform-backend.sh` and an AWS account.
- Never commit `*.tfstate`, `*.tfvars` (only `*.tfvars.example`), or plan files.
- Use `lifecycle { prevent_destroy = true }` on stateful resources in prod (state buckets, KMS keys, RDS, artifact buckets).
- Review every `plan` for unexpected `destroy` / `replace`; call them out explicitly when proposing changes.
- Agents may run `terraform fmt`, `validate`, `init -backend=false` and `make test-terraform-plan`. They must not run `apply`, `destroy` or `import` unless explicitly asked.

## Security defaults

- Encryption with KMS on S3, EBS, EKS secrets, ECR, CloudWatch logs.
- Private subnets for nodes; NAT per AZ in prod; VPC endpoints for S3/ECR/STS to cut NAT cost and exposure.
- Security groups: no `0.0.0.0/0` ingress except on public load balancers on 443.
- Scan with `tflint`, `tfsec`/`trivy config` or `checkov` when available.

## Testing

- Module tests live in `infra/modules/<name>/test/` (Terratest). `make test` hits real AWS; prefer `make test-terraform-plan` locally and in CI.
