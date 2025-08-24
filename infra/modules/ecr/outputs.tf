# ECR Module Outputs

output "repository_urls" {
  description = "Map of repository names to their URLs"
  value       = { for k, v in aws_ecr_repository.repositories : k => v.repository_url }
}

output "repository_arns" {
  description = "Map of repository names to their ARNs"
  value       = { for k, v in aws_ecr_repository.repositories : k => v.arn }
}

output "repository_registry_ids" {
  description = "Map of repository names to their registry IDs"
  value       = { for k, v in aws_ecr_repository.repositories : k => v.registry_id }
}

output "repository_names" {
  description = "Map of repository keys to their names"
  value       = { for k, v in aws_ecr_repository.repositories : k => v.name }
}