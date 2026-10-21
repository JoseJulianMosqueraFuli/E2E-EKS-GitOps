# Staging Environment Outputs

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
  value       = module.ecr.repository_urls
}

output "kms_key_arn" {
  description = "ARN of KMS key"
  value       = aws_kms_key.main.arn
}
output "workload_role_arns" {
  description = "IRSA roles for MLflow, Argo workflows and database backups"
  value       = module.workload_identity.role_arns
}

output "platform_config" {
  description = "Non-secret values consumed by GitOps platform renderers"
  value = {
    AWS_ACCOUNT_ID = data.aws_caller_identity.current.account_id
    AWS_REGION     = var.aws_region
  }
}

output "flux_runtime_config" {
  description = "Cloud values to merge into gitops/platform/flux.env.example"
  value = {
    aws_account_id = data.aws_caller_identity.current.account_id
    region         = var.aws_region
    cluster_name   = module.eks.cluster_id
    vpc_id         = module.vpc.vpc_id
    kms_key_id     = aws_kms_key.main.arn
    alb_irsa_role  = module.eks.aws_load_balancer_controller_role_arn
    ebs_irsa_role  = module.eks.ebs_csi_driver_role_arn
    ca_irsa_role   = module.eks.cluster_autoscaler_role_arn
  }
}
