output "role_arns" {
  description = "IAM roles consumed by GitOps ServiceAccounts"
  value       = { for name, role in aws_iam_role.workload : name => role.arn }
}
