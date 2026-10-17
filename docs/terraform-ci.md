# Terraform validation and initial plans in GitHub Actions

Terraform runs on GitHub-hosted runners. No local cluster, Docker build, or AWS deployment is needed.
Standard GitHub-hosted runners are free for public repositories; larger runners and storage have separate
billing rules ([GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)).

| Workflow | Trigger | Environments | AWS access | Result |
|---|---|---|---|---|
| `CI Pipeline` (`ci.yml`) | Push, pull request, or manual run | `dev`, `staging`, `prod` | None for Terraform validation | Format check, initialization without backend, and validation |
| `Terraform Initial Plan` (`terraform-plan.yml`) | Manual run from `main` | Select `dev`, `staging`, or `prod` | OIDC role restricted to discovery reads | Speculative plan from empty state |

The initial plan uses the real AWS provider. It reads the account identity and available zones, then
calculates the resources to create using the selected environment's defaults and `AWS_REGION`. It does
not create infrastructure, run Terratest, or execute `apply`.

## Configure the first AWS plan

1. In AWS IAM, configure the GitHub OIDC provider `https://token.actions.githubusercontent.com`, with
   audience `sts.amazonaws.com`. Reuse the provider if it already exists. This can be done in the AWS
   console without running anything on your machine.
2. Create a dedicated planning role. Grant only `sts:GetCallerIdentity` and
   `ec2:DescribeAvailabilityZones`. These discovery actions require `Resource: "*"` because they do not
   support resource-level permissions. The workflow also restricts the assumed session to these actions.
3. Restrict the role's trust policy to this repository and the selected GitHub environment. For `dev`,
   the standard subject is:

   ```text
   repo:JoseJulianMosqueraFuli/E2E-EKS-GitOps:environment:terraform-plan-dev
   ```

   Require `token.actions.githubusercontent.com:aud` to equal `sts.amazonaws.com` and
   `token.actions.githubusercontent.com:sub` to equal that exact subject. If the repository uses
   immutable OIDC subjects, use its actual subject with owner/repository IDs instead. See the
   [GitHub AWS OIDC guide](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).
4. In GitHub, create the environment `terraform-plan-dev` under **Settings → Environments**. Restrict
   its deployment branches to `main`. Set these environment variables:

   | Variable | Value |
   |---|---|
   | `AWS_PLAN_ROLE_ARN` | ARN of the dedicated AWS planning role |
   | `AWS_REGION` | Region to use for the plan |

5. Once the workflow is merged into `main`, open **Actions → Terraform Initial Plan → Run workflow**,
   select branch `main` and environment `dev`.
6. Check the **Generate initial plan** log and the run summary. Terraform exit code `2` means the plan
   succeeded and proposes changes; errors still fail the job.

For `staging` and `prod`, create `terraform-plan-staging` and `terraform-plan-prod` with their own
variables and corresponding trusted OIDC subjects. The workflow and validation support all three.

AWS access is limited to manual runs from `main`. Pull requests, including forks, receive only the
credential-free Terraform validation job. No long-lived AWS access keys are needed. Plan output is
visible in the public Actions log; the credential action masks the AWS account ID. No binary plan,
state, or plan JSON is uploaded as an artifact.

## State and scope

This workflow is for an environment's **first deployment planning only**. It copies the infrastructure
source to a temporary directory on the runner, excludes state and variable files, and overrides the
backend to use local temporary state. The repository's backend configuration is unchanged. The copy
is removed when the script exits. There is no saved plan to apply later.

An empty-state plan does not discover resources already managed by Terraform and cannot report drift
or changes to an existing deployment. Before planning updates to deployed infrastructure, finish
HIGH-001 and configure a separate workflow against the correct remote state and its required read/lock
permissions. Do not use the initial plan as a replacement for that workflow. A successful plan also
does not prove that bucket names are available or that AWS will permit a subsequent deployment.

The initial plan does not load local `terraform.tfvars` or `*.auto.tfvars` files. Environment sizing
comes from the committed variable defaults. AWS account and region values stay in GitHub configuration,
not in committed manifests or documentation.

## Commands and provider scope

The workflows use the repository's Make targets:

```bash
make terraform-fmt-check
make validate-terraform ENV=dev
make terraform-initial-plan ENV=dev
```

`terraform-initial-plan` requires GitHub Actions and refuses local execution. `test-terraform-plan`
remains a compatibility alias for `validate-terraform`; it does not generate a plan. Existing `make plan`
behavior is unchanged.

This automation targets GitHub Actions because it is the requested execution platform. GitLab,
CircleCI, and Jenkins retain their existing workflows; they can use the common validation targets.
No AWS deployment or Terratest run is enabled by these changes. ECR publishing through OIDC remains a
separate task (backlog #55).
