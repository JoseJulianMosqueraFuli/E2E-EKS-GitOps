output "role_arn" {
  description = "GitHub Actions AWS_ROLE_ARN for the protected environment"
  value       = aws_iam_role.publisher.arn
}
