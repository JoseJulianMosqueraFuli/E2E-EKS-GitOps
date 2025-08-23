# Development Environment Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "eks_cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "s3_bucket_arns" {
  description = "ARNs of S3 buckets"
  value       = module.s3.bucket_arns
}

output "ecr_repository_urls" {
  description = "URLs of ECR repositories"
  value = {
    trainer   = aws_ecr_repository.trainer.repository_url
    inference = aws_ecr_repository.inference.repository_url
  }
}

output "kms_key_arn" {
  description = "ARN of KMS key"
  value       = aws_kms_key.main.arn
}