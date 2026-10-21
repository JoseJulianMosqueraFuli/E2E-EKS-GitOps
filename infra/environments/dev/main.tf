# Development Environment Configuration

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "dev"
      Project     = "mlops-platform"
      ManagedBy   = "terraform"
    }
  }
}

# Local variables
locals {
  name_prefix = "mlops-dev"

  common_tags = {
    Environment = "dev"
    Project     = "mlops-platform"
    ManagedBy   = "terraform"
  }
}

# KMS Key for encryption
resource "aws_kms_key" "main" {
  description             = "KMS key for MLOps platform encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = local.common_tags
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name_prefix}-key"
  target_key_id = aws_kms_key.main.key_id
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  public_subnet_count  = var.public_subnet_count
  private_subnet_count = var.private_subnet_count
  enable_nat_gateway   = var.enable_nat_gateway

  # HIGH-003: Restrict node egress to VPC only, plus any extra CIDRs.
  node_egress_cidrs = concat([var.vpc_cidr], var.node_egress_cidrs)

  tags = local.common_tags
}

# EKS Module
module "eks" {
  source = "../../modules/eks"

  cluster_name       = "${local.name_prefix}-cluster"
  kubernetes_version = var.kubernetes_version

  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids

  endpoint_public_access = false
  public_access_cidrs    = []

  kms_key_arn = aws_kms_key.main.arn

  node_group_instance_types = var.node_group_instance_types
  node_group_desired_size   = var.node_group_desired_size
  node_group_max_size       = var.node_group_max_size
  node_group_min_size       = var.node_group_min_size

  # Optional GPU node group (disabled by default)
  enable_gpu_node_group         = var.enable_gpu_node_group
  gpu_node_group_instance_types = var.gpu_node_group_instance_types
  gpu_node_group_desired_size   = var.gpu_node_group_desired_size
  gpu_node_group_max_size       = var.gpu_node_group_max_size
  gpu_node_group_min_size       = var.gpu_node_group_min_size

  tags = local.common_tags
}

# S3 Buckets Module
module "s3" {
  source = "../../modules/s3"

  kms_key_arn = aws_kms_key.main.arn

  buckets = {
    raw_data = {
      name               = "${local.name_prefix}-raw-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      versioning_enabled = true
      force_destroy      = false
      tags               = { Purpose = "raw-data-storage" }
      lifecycle_rules = [
        {
          id      = "raw_data_lifecycle"
          enabled = true
          transitions = [
            {
              days          = 30
              storage_class = "STANDARD_IA"
            },
            {
              days          = 90
              storage_class = "GLACIER"
            }
          ]
        }
      ]
    }

    curated_data = {
      name               = "${local.name_prefix}-curated-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      versioning_enabled = true
      force_destroy      = false
      tags               = { Purpose = "curated-data-storage" }
      lifecycle_rules = [
        {
          id      = "curated_data_lifecycle"
          enabled = true
          transitions = [
            {
              days          = 60
              storage_class = "STANDARD_IA"
            }
          ]
        }
      ]
    }

    backups = {
      name               = "${local.name_prefix}-backups-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      versioning_enabled = true
      force_destroy      = false
      tags               = { Purpose = "database-backups" }
    }
    model_artifacts = {
      name               = "${local.name_prefix}-model-artifacts-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      versioning_enabled = true
      force_destroy      = false
      tags               = { Purpose = "model-storage" }
    }
  }

  tags = local.common_tags
}

# ECR Module
module "ecr" {
  source = "../../modules/ecr"

  kms_key_arn = aws_kms_key.main.arn

  repositories = {
    trainer = {
      name                 = "${local.name_prefix}-trainer"
      image_tag_mutability = "MUTABLE"
      scan_on_push         = true
      tags                 = { Purpose = "ml-training" }
    }
    inference = {
      name                 = "${local.name_prefix}-inference"
      image_tag_mutability = "MUTABLE"
      scan_on_push         = true
      tags                 = { Purpose = "ml-inference" }
    }
    feature_transformer = {
      name                 = "${local.name_prefix}-feature-transformer"
      image_tag_mutability = "MUTABLE"
      scan_on_push         = true
      tags                 = { Purpose = "feature-processing" }
    }
    monitoring = {
      name                 = "${local.name_prefix}-monitoring"
      image_tag_mutability = "IMMUTABLE"
      scan_on_push         = true
      tags                 = { Purpose = "model-monitoring" }
    }
    mlflow_server = {
      name                 = "${local.name_prefix}-mlflow-server"
      image_tag_mutability = "MUTABLE"
      scan_on_push         = true
      tags                 = { Purpose = "experiment-tracking" }
    }
  }

  allowed_principals = [
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
  ]

  enable_registry_scanning = true

  tags = local.common_tags
}

# Glue Data Catalog Module
module "glue" {
  source = "../../modules/glue"

  name_prefix = local.name_prefix

  databases = {
    mlops_raw = {
      name        = "${local.name_prefix}-raw-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      description = "Raw data catalog for MLOps pipeline"
    }
    mlops_curated = {
      name        = "${local.name_prefix}-curated-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      description = "Curated data catalog for MLOps pipeline"
    }
    mlops_features = {
      name        = "${local.name_prefix}-features"
      description = "Feature store catalog for MLOps pipeline"
    }
  }

  tables = {
    raw_training_data = {
      name          = "training_data"
      database_name = "${local.name_prefix}-raw-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      description   = "Raw training data table"
      table_type    = "EXTERNAL_TABLE"
      storage_descriptor = {
        location      = "s3://${module.s3.bucket_ids["raw_data"]}/training-data/"
        input_format  = "org.apache.hadoop.mapred.TextInputFormat"
        output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"
        ser_de_info = {
          serialization_library = "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
          parameters = {
            "field.delim" = ","
          }
        }
        columns = [
          {
            name = "feature_1"
            type = "double"
          },
          {
            name = "feature_2"
            type = "double"
          },
          {
            name = "target"
            type = "double"
          }
        ]
      }
    }
  }

  crawlers = {
    raw_data_crawler = {
      name          = "${local.name_prefix}-raw-data-crawler"
      database_name = "${local.name_prefix}-raw-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      description   = "Crawler for raw ML data"
      schedule      = "cron(0 2 * * ? *)" # Daily at 2 AM
      s3_targets = [
        {
          path = "s3://${module.s3.bucket_ids["raw_data"]}/"
        }
      ]
      schema_change_policy = {
        update_behavior = "UPDATE_IN_DATABASE"
        delete_behavior = "LOG"
      }
      tags = { Purpose = "raw-data-discovery" }
    }
    curated_data_crawler = {
      name          = "${local.name_prefix}-curated-data-crawler"
      database_name = "${local.name_prefix}-curated-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
      description   = "Crawler for curated ML data"
      schedule      = "cron(0 3 * * ? *)" # Daily at 3 AM
      s3_targets = [
        {
          path = "s3://${module.s3.bucket_ids["curated_data"]}/"
        }
      ]
      schema_change_policy = {
        update_behavior = "UPDATE_IN_DATABASE"
        delete_behavior = "LOG"
      }
      tags = { Purpose = "curated-data-discovery" }
    }
  }

  data_quality_rulesets = {
    training_data_quality = {
      name        = "${local.name_prefix}-training-data-quality"
      description = "Data quality rules for training data"
      ruleset     = <<-EOT
        Rules = [
          ColumnCount > 0,
          IsComplete "feature_1",
          IsComplete "feature_2",
          IsComplete "target",
          ColumnDataType "feature_1" = "NUMERIC",
          ColumnDataType "feature_2" = "NUMERIC",
          ColumnDataType "target" = "NUMERIC"
        ]
      EOT
      target_table = {
        database_name = "${local.name_prefix}-raw-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
        table_name    = "training_data"
      }
      tags = { Purpose = "data-quality-validation" }
    }
  }

  s3_bucket_arns = [
    module.s3.bucket_arns["raw_data"],
    module.s3.bucket_arns["curated_data"],
    module.s3.bucket_arns["model_artifacts"]
  ]

  tags = local.common_tags
}

# Data sources
data "aws_caller_identity" "current" {}
module "workload_identity" {
  source                   = "../../modules/workload-identity"
  name_prefix              = local.name_prefix
  environment              = "dev"
  oidc_provider_arn        = module.eks.oidc_provider_arn
  oidc_provider_url        = module.eks.oidc_provider_url
  bucket_arns              = module.s3.bucket_arns
  kms_key_arn              = aws_kms_key.main.arn
  inference_repository_arn = module.ecr.repository_arns["inference"]
  tags                     = local.common_tags
}

module "ecr_publisher" {
  source               = "../../modules/ecr-publisher"
  name_prefix          = local.name_prefix
  environment          = "dev"
  repository           = var.github_repository
  oidc_provider_arn    = var.github_oidc_provider_arn
  create_oidc_provider = true
  repository_arns      = [for name in ["trainer", "mlflow_server", "monitoring"] : module.ecr.repository_arns[name]]
  tags                 = local.common_tags
}
