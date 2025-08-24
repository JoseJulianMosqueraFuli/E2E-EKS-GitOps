# Glue Module Variables

variable "name_prefix" {
  description = "Name prefix for all resources"
  type        = string
}

variable "databases" {
  description = "Map of Glue catalog database configurations"
  type = map(object({
    name         = string
    description  = optional(string)
    catalog_id   = optional(string)
    location_uri = optional(string)
    create_table_default_permissions = optional(list(object({
      permissions = list(string)
      principal   = string
    })))
    target_database = optional(object({
      catalog_id    = string
      database_name = string
    }))
  }))
  default = {}
}

variable "tables" {
  description = "Map of Glue catalog table configurations"
  type = map(object({
    name          = string
    database_name = string
    catalog_id    = optional(string)
    description   = optional(string)
    table_type    = optional(string)
    parameters    = optional(map(string))
    storage_descriptor = optional(object({
      location                  = optional(string)
      input_format             = optional(string)
      output_format            = optional(string)
      compressed               = optional(bool)
      number_of_buckets        = optional(number)
      bucket_columns           = optional(list(string))
      parameters               = optional(map(string))
      stored_as_sub_directories = optional(bool)
      columns = optional(list(object({
        name    = string
        type    = string
        comment = optional(string)
      })))
      ser_de_info = optional(object({
        name                  = optional(string)
        serialization_library = optional(string)
        parameters            = optional(map(string))
      }))
      sort_columns = optional(list(object({
        column     = string
        sort_order = number
      })))
      skewed_info = optional(object({
        skewed_column_names               = optional(list(string))
        skewed_column_value_location_maps = optional(map(string))
        skewed_column_values              = optional(list(string))
      }))
    }))
    partition_keys = optional(list(object({
      name    = string
      type    = string
      comment = optional(string)
    })))
    target_table = optional(object({
      catalog_id    = string
      database_name = string
      name          = string
    }))
  }))
  default = {}
}

variable "crawlers" {
  description = "Map of Glue crawler configurations"
  type = map(object({
    database_name = string
    name          = string
    role          = optional(string)
    description   = optional(string)
    schedule      = optional(string)
    configuration = optional(string)
    tags          = optional(map(string))
    s3_targets = optional(list(object({
      path                = string
      exclusions          = optional(list(string))
      connection_name     = optional(string)
      sample_size         = optional(number)
      event_queue_arn     = optional(string)
      dlq_event_queue_arn = optional(string)
    })))
    jdbc_targets = optional(list(object({
      connection_name = string
      path            = string
      exclusions      = optional(list(string))
    })))
    mongodb_targets = optional(list(object({
      connection_name = string
      path            = string
      scan_all        = optional(bool)
    })))
    dynamodb_targets = optional(list(object({
      path      = string
      scan_all  = optional(bool)
      scan_rate = optional(number)
    })))
    catalog_targets = optional(list(object({
      database_name = string
      tables        = list(string)
    })))
    schema_change_policy = optional(object({
      update_behavior = optional(string)
      delete_behavior = optional(string)
    }))
    recrawl_policy = optional(object({
      recrawl_behavior = string
    }))
    lineage_configuration = optional(object({
      crawler_lineage_settings = string
    }))
  }))
  default = {}
}

variable "data_quality_rulesets" {
  description = "Map of Glue data quality ruleset configurations"
  type = map(object({
    name        = string
    description = optional(string)
    ruleset     = string
    tags        = optional(map(string))
    target_table = optional(object({
      database_name = string
      table_name    = string
      catalog_id    = optional(string)
    }))
  }))
  default = {}
}

variable "create_crawler_role" {
  description = "Whether to create a default IAM role for crawlers"
  type        = bool
  default     = true
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs that crawlers need access to"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}