# S3 Module
# Creates S3 buckets for ML data storage with encryption and versioning

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# S3 Buckets
resource "aws_s3_bucket" "buckets" {
  for_each = var.buckets

  bucket        = each.value.name
  force_destroy = each.value.force_destroy

  tags = merge(var.tags, each.value.tags, {
    Name = each.value.name
  })
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "buckets" {
  for_each = var.buckets

  bucket = aws_s3_bucket.buckets[each.key].id
  versioning_configuration {
    status = each.value.versioning_enabled ? "Enabled" : "Disabled"
  }
}

# S3 Bucket Server Side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "buckets" {
  for_each = var.buckets

  bucket = aws_s3_bucket.buckets[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "buckets" {
  for_each = var.buckets

  bucket = aws_s3_bucket.buckets[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "buckets" {
  for_each = { for k, v in var.buckets : k => v if v.lifecycle_rules != null }

  bucket = aws_s3_bucket.buckets[each.key].id

  dynamic "rule" {
    for_each = each.value.lifecycle_rules
    content {
      id     = rule.value.id
      status = rule.value.enabled ? "Enabled" : "Disabled"

      dynamic "expiration" {
        for_each = rule.value.expiration_days != null ? [1] : []
        content {
          days = rule.value.expiration_days
        }
      }

      dynamic "noncurrent_version_expiration" {
        for_each = rule.value.noncurrent_version_expiration_days != null ? [1] : []
        content {
          noncurrent_days = rule.value.noncurrent_version_expiration_days
        }
      }

      dynamic "transition" {
        for_each = rule.value.transitions != null ? rule.value.transitions : []
        content {
          days          = transition.value.days
          storage_class = transition.value.storage_class
        }
      }
    }
  }
}

# S3 Bucket Notification
resource "aws_s3_bucket_notification" "buckets" {
  for_each = { for k, v in var.buckets : k => v if v.notification_config != null }

  bucket = aws_s3_bucket.buckets[each.key].id

  dynamic "lambda_function" {
    for_each = each.value.notification_config.lambda_functions != null ? each.value.notification_config.lambda_functions : []
    content {
      lambda_function_arn = lambda_function.value.lambda_function_arn
      events              = lambda_function.value.events
      filter_prefix       = lambda_function.value.filter_prefix
      filter_suffix       = lambda_function.value.filter_suffix
    }
  }

  dynamic "topic" {
    for_each = each.value.notification_config.sns_topics != null ? each.value.notification_config.sns_topics : []
    content {
      topic_arn     = topic.value.topic_arn
      events        = topic.value.events
      filter_prefix = topic.value.filter_prefix
      filter_suffix = topic.value.filter_suffix
    }
  }
}