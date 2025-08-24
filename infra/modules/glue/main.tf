# Glue Module
# Creates AWS Glue Data Catalog resources for ML data management

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Glue Catalog Database
resource "aws_glue_catalog_database" "databases" {
  for_each = var.databases

  name         = each.value.name
  description  = each.value.description
  catalog_id   = each.value.catalog_id
  location_uri = each.value.location_uri

  dynamic "create_table_default_permission" {
    for_each = each.value.create_table_default_permissions != null ? each.value.create_table_default_permissions : []
    content {
      permissions = create_table_default_permission.value.permissions
      principal   = create_table_default_permission.value.principal
    }
  }

  dynamic "target_database" {
    for_each = each.value.target_database != null ? [each.value.target_database] : []
    content {
      catalog_id    = target_database.value.catalog_id
      database_name = target_database.value.database_name
    }
  }
}

# Glue Catalog Table
resource "aws_glue_catalog_table" "tables" {
  for_each = var.tables

  name          = each.value.name
  database_name = each.value.database_name
  catalog_id    = each.value.catalog_id
  description   = each.value.description
  table_type    = each.value.table_type
  parameters    = each.value.parameters

  dynamic "storage_descriptor" {
    for_each = each.value.storage_descriptor != null ? [each.value.storage_descriptor] : []
    content {
      location                  = storage_descriptor.value.location
      input_format             = storage_descriptor.value.input_format
      output_format            = storage_descriptor.value.output_format
      compressed               = storage_descriptor.value.compressed
      number_of_buckets        = storage_descriptor.value.number_of_buckets
      bucket_columns           = storage_descriptor.value.bucket_columns
      parameters               = storage_descriptor.value.parameters
      stored_as_sub_directories = storage_descriptor.value.stored_as_sub_directories

      dynamic "columns" {
        for_each = storage_descriptor.value.columns != null ? storage_descriptor.value.columns : []
        content {
          name    = columns.value.name
          type    = columns.value.type
          comment = columns.value.comment
        }
      }

      dynamic "ser_de_info" {
        for_each = storage_descriptor.value.ser_de_info != null ? [storage_descriptor.value.ser_de_info] : []
        content {
          name                  = ser_de_info.value.name
          serialization_library = ser_de_info.value.serialization_library
          parameters            = ser_de_info.value.parameters
        }
      }

      dynamic "sort_columns" {
        for_each = storage_descriptor.value.sort_columns != null ? storage_descriptor.value.sort_columns : []
        content {
          column     = sort_columns.value.column
          sort_order = sort_columns.value.sort_order
        }
      }

      dynamic "skewed_info" {
        for_each = storage_descriptor.value.skewed_info != null ? [storage_descriptor.value.skewed_info] : []
        content {
          skewed_column_names               = skewed_info.value.skewed_column_names
          skewed_column_value_location_maps = skewed_info.value.skewed_column_value_location_maps
          skewed_column_values              = skewed_info.value.skewed_column_values
        }
      }
    }
  }

  dynamic "partition_keys" {
    for_each = each.value.partition_keys != null ? each.value.partition_keys : []
    content {
      name    = partition_keys.value.name
      type    = partition_keys.value.type
      comment = partition_keys.value.comment
    }
  }

  dynamic "target_table" {
    for_each = each.value.target_table != null ? [each.value.target_table] : []
    content {
      catalog_id    = target_table.value.catalog_id
      database_name = target_table.value.database_name
      name          = target_table.value.name
    }
  }
}

# Glue Crawler IAM Role
resource "aws_iam_role" "glue_crawler" {
  count = var.create_crawler_role ? 1 : 0
  name  = "${var.name_prefix}-glue-crawler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  count      = var.create_crawler_role ? 1 : 0
  role       = aws_iam_role.glue_crawler[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3_access" {
  count = var.create_crawler_role ? 1 : 0
  name  = "${var.name_prefix}-glue-s3-access"
  role  = aws_iam_role.glue_crawler[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket",
          "s3:ListAllMyBuckets",
          "s3:GetBucketAcl"
        ]
        Resource = var.s3_bucket_arns
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [for arn in var.s3_bucket_arns : "${arn}/*"]
      }
    ]
  })
}

# Glue Crawler
resource "aws_glue_crawler" "crawlers" {
  for_each = var.crawlers

  database_name = each.value.database_name
  name          = each.value.name
  role          = var.create_crawler_role ? aws_iam_role.glue_crawler[0].arn : each.value.role
  description   = each.value.description
  schedule      = each.value.schedule

  dynamic "s3_target" {
    for_each = each.value.s3_targets != null ? each.value.s3_targets : []
    content {
      path                = s3_target.value.path
      exclusions          = s3_target.value.exclusions
      connection_name     = s3_target.value.connection_name
      sample_size         = s3_target.value.sample_size
      event_queue_arn     = s3_target.value.event_queue_arn
      dlq_event_queue_arn = s3_target.value.dlq_event_queue_arn
    }
  }

  dynamic "jdbc_target" {
    for_each = each.value.jdbc_targets != null ? each.value.jdbc_targets : []
    content {
      connection_name = jdbc_target.value.connection_name
      path            = jdbc_target.value.path
      exclusions      = jdbc_target.value.exclusions
    }
  }

  dynamic "mongodb_target" {
    for_each = each.value.mongodb_targets != null ? each.value.mongodb_targets : []
    content {
      connection_name = mongodb_target.value.connection_name
      path            = mongodb_target.value.path
      scan_all        = mongodb_target.value.scan_all
    }
  }

  dynamic "dynamodb_target" {
    for_each = each.value.dynamodb_targets != null ? each.value.dynamodb_targets : []
    content {
      path      = dynamodb_target.value.path
      scan_all  = dynamodb_target.value.scan_all
      scan_rate = dynamodb_target.value.scan_rate
    }
  }

  dynamic "catalog_target" {
    for_each = each.value.catalog_targets != null ? each.value.catalog_targets : []
    content {
      database_name = catalog_target.value.database_name
      tables        = catalog_target.value.tables
    }
  }

  dynamic "schema_change_policy" {
    for_each = each.value.schema_change_policy != null ? [each.value.schema_change_policy] : []
    content {
      update_behavior = schema_change_policy.value.update_behavior
      delete_behavior = schema_change_policy.value.delete_behavior
    }
  }

  dynamic "recrawl_policy" {
    for_each = each.value.recrawl_policy != null ? [each.value.recrawl_policy] : []
    content {
      recrawl_behavior = recrawl_policy.value.recrawl_behavior
    }
  }

  dynamic "lineage_configuration" {
    for_each = each.value.lineage_configuration != null ? [each.value.lineage_configuration] : []
    content {
      crawler_lineage_settings = lineage_configuration.value.crawler_lineage_settings
    }
  }

  configuration = each.value.configuration

  tags = merge(var.tags, each.value.tags, {
    Name = each.value.name
  })
}

# Glue Data Quality Ruleset
resource "aws_glue_data_quality_ruleset" "rulesets" {
  for_each = var.data_quality_rulesets

  name        = each.value.name
  description = each.value.description
  ruleset     = each.value.ruleset

  dynamic "target_table" {
    for_each = each.value.target_table != null ? [each.value.target_table] : []
    content {
      database_name = target_table.value.database_name
      table_name    = target_table.value.table_name
      catalog_id    = target_table.value.catalog_id
    }
  }

  tags = merge(var.tags, each.value.tags, {
    Name = each.value.name
  })
}