variable "name_prefix" {
  type        = string
  description = "Environment-specific platform prefix"
}
variable "environment" {
  type        = string
  description = "Kustomize environment prefix (dev, staging or prod)"
}
variable "oidc_provider_arn" {
  type        = string
  description = "EKS OIDC provider ARN"
}
variable "oidc_provider_url" {
  type        = string
  description = "EKS OIDC issuer without the HTTPS scheme"
}
variable "bucket_arns" {
  type        = map(string)
  description = "Platform S3 bucket ARNs keyed by purpose"
}
variable "kms_key_arn" {
  type        = string
  description = "Platform encryption key ARN"
}
variable "inference_repository_arn" {
  type        = string
  description = "ECR repository for images built by model deployment workflows"
}
variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
