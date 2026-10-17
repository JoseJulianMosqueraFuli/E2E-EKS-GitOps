#!/usr/bin/env bash
set -euo pipefail

environment="${1:-}"
case "$environment" in
  dev|staging|prod) ;;
  *) echo "Usage: bash scripts/terraform-initial-plan.sh <dev|staging|prod>" >&2; exit 1 ;;
esac

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "Run Terraform Initial Plan from GitHub Actions; local AWS planning is disabled here." >&2
  exit 1
fi

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plan_directory="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/terraform-initial-plan.XXXXXX")"
trap 'rm -rf "$plan_directory"' EXIT

tar -C "$repository_root" \
  --exclude=.terraform \
  --exclude='*.tfstate*' \
  --exclude='*.tfvars' \
  --exclude='*.tfvars.json' \
  --exclude='*.tfplan' \
  -cf - infra | tar -C "$plan_directory" -xf -

terraform_root="$plan_directory/infra/environments/$environment"
printf 'terraform {\n  backend "local" {}\n}\n' > "$terraform_root/zz_initial_plan_override.tf"

echo "Initial $environment plan against empty temporary state, using environment defaults and TF_VAR_aws_region."
terraform -chdir="$terraform_root" init -input=false -no-color
terraform -chdir="$terraform_root" validate -no-color

if terraform -chdir="$terraform_root" plan -input=false -no-color -detailed-exitcode; then
  result="No changes proposed."
else
  status=$?
  if [[ "$status" -ne 2 ]]; then
    exit "$status"
  fi
  result="Changes proposed; see the Generate initial plan step for details."
fi

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    printf '### Initial Terraform plan: %s\n\n' "$environment"
    printf '%s\n\n' "$result"
    printf 'This speculative plan used empty temporary state and the real AWS provider. '
    printf 'It does not compare against an existing deployment. No changes were applied and no plan artifact was saved.\n'
  } >> "$GITHUB_STEP_SUMMARY"
fi
