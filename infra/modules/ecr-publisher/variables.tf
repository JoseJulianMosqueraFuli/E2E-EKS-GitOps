variable "name_prefix" {
  type        = string
  description = "Environment-specific role name prefix"
}
variable "environment" {
  type        = string
  description = "Protected GitHub Actions environment"
}
variable "repository" {
  type        = string
  description = "GitHub owner/repository authorized to publish"
}
variable "repository_arns" {
  type        = list(string)
  description = "Exact ECR repositories the publisher can write"
}
variable "oidc_provider_arn" {
  type        = string
  description = "Existing GitHub OIDC provider ARN, or null to use the account provider"
  default     = null
}
variable "create_oidc_provider" {
  type        = bool
  description = "Create the account-wide GitHub OIDC provider when no ARN is supplied"
  default     = false
}
variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
