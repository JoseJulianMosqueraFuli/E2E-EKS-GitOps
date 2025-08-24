# S3 Module Variables

variable "buckets" {
  description = "Map of S3 bucket configurations"
  type = map(object({
    name                = string
    versioning_enabled  = bool
    force_destroy       = bool
    tags                = map(string)
    bucket_policy       = optional(string)
    lifecycle_rules = optional(list(object({
      id                                    = string
      enabled                              = bool
      expiration_days                      = optional(number)
      noncurrent_version_expiration_days   = optional(number)
      transitions = optional(list(object({
        days          = number
        storage_class = string
      })))
    })))
    notification_config = optional(object({
      lambda_functions = optional(list(object({
        lambda_function_arn = string
        events              = list(string)
        filter_prefix       = optional(string)
        filter_suffix       = optional(string)
      })))
      sns_topics = optional(list(object({
        topic_arn     = string
        events        = list(string)
        filter_prefix = optional(string)
        filter_suffix = optional(string)
      })))
    }))
    logging_config = optional(object({
      target_bucket = string
      target_prefix = string
    }))
    cors_rules = optional(list(object({
      allowed_headers = optional(list(string))
      allowed_methods = list(string)
      allowed_origins = list(string)
      expose_headers  = optional(list(string))
      max_age_seconds = optional(number)
    })))
    replication_config = optional(object({
      role_arn = string
      rules = list(object({
        id     = string
        status = string
        filter = optional(object({
          prefix = optional(string)
          tags   = optional(map(string))
        }))
        destination = object({
          bucket        = string
          storage_class = optional(string)
          kms_key_id    = optional(string)
        })
      }))
    }))
  }))
}

variable "kms_key_arn" {
  description = "ARN of KMS key for S3 encryption"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}