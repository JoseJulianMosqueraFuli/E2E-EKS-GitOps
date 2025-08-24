# Glue Module Outputs

output "database_names" {
  description = "Map of database keys to their names"
  value       = { for k, v in aws_glue_catalog_database.databases : k => v.name }
}

output "database_catalog_ids" {
  description = "Map of database keys to their catalog IDs"
  value       = { for k, v in aws_glue_catalog_database.databases : k => v.catalog_id }
}

output "table_names" {
  description = "Map of table keys to their names"
  value       = { for k, v in aws_glue_catalog_table.tables : k => v.name }
}

output "crawler_names" {
  description = "Map of crawler keys to their names"
  value       = { for k, v in aws_glue_crawler.crawlers : k => v.name }
}

output "crawler_arns" {
  description = "Map of crawler keys to their ARNs"
  value       = { for k, v in aws_glue_crawler.crawlers : k => v.arn }
}

output "crawler_role_arn" {
  description = "ARN of the Glue crawler IAM role"
  value       = var.create_crawler_role ? aws_iam_role.glue_crawler[0].arn : null
}

output "data_quality_ruleset_names" {
  description = "Map of data quality ruleset keys to their names"
  value       = { for k, v in aws_glue_data_quality_ruleset.rulesets : k => v.name }
}