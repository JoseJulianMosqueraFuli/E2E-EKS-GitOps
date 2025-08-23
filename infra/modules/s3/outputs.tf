# S3 Module Outputs

output "bucket_ids" {
  description = "Map of bucket names to their IDs"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.id }
}

output "bucket_arns" {
  description = "Map of bucket names to their ARNs"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.arn }
}

output "bucket_domain_names" {
  description = "Map of bucket names to their domain names"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.bucket_domain_name }
}

output "bucket_regional_domain_names" {
  description = "Map of bucket names to their regional domain names"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.bucket_regional_domain_name }
}