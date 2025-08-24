# ECR Module Variables

variable "repositories" {
  description = "Map of ECR repository configurations"
  type = map(object({
    name                 = string
    image_tag_mutability = string
    scan_on_push         = bool
    tags                 = map(string)
    repository_policy    = optional(string)
    lifecycle_policy     = optional(string)
  }))
}

variable "kms_key_arn" {
  description = "ARN of KMS key for ECR encryption"
  type        = string
}

variable "allowed_principals" {
  description = "List of AWS principals allowed to access ECR repositories"
  type        = list(string)
  default     = []
}

variable "enable_registry_scanning" {
  description = "Enable enhanced scanning for the ECR registry"
  type        = bool
  default     = true
}

variable "replication_configuration" {
  description = "ECR replication configuration"
  type = object({
    rules = list(object({
      destinations = list(object({
        region      = string
        registry_id = string
      }))
      repository_filters = optional(list(object({
        filter      = string
        filter_type = string
      })))
    }))
  })
  default = null
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}