# Development Environment Configuration

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Configure backend in terraform init
    # bucket = "mlops-terraform-state-dev"
    # key    = "dev/terraform.tfstate"
    # region = "us-east-1"
  }
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

  tags = local.common_tags
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name_prefix}-key"
  target_key_id = aws_kms_key.main.key_id
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  name_prefix           = local.name_prefix
  vpc_cidr              = var.vpc_cidr
  public_subnet_count   = var.public_subnet_count
  private_subnet_count  = var.private_subnet_count
  enable_nat_gateway    = var.enable_nat_gateway

  tags = local.common_tags
}

# EKS Module
module "eks" {
  source = "../../modules/eks"

  cluster_name       = "${local.name_prefix}-cluster"
  kubernetes_version = var.kubernetes_version
  
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  
  kms_key_arn = aws_kms_key.main.arn
  
  node_group_instance_types = var.node_group_instance_types
  node_group_desired_size   = var.node_group_desired_size
  node_group_max_size       = var.node_group_max_size
  node_group_min_size       = var.node_group_min_size

  tags = local.common_tags
}

# S3 Buckets Module
module "s3" {
  source = "../../modules/s3"

  kms_key_arn = aws_kms_key.main.arn
  
  buckets = {
    raw_data = {
      name               = "${local.name_prefix}-raw-data"
      versioning_enabled = true
      force_destroy      = true
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
      name               = "${local.name_prefix}-curated-data"
      versioning_enabled = true
      force_destroy      = true
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
    
    model_artifacts = {
      name               = "${local.name_prefix}-model-artifacts"
      versioning_enabled = true
      force_destroy      = true
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
      name        = "${local.name_prefix}-raw-data"
      description = "Raw data catalog for MLOps pipeline"
    }
    mlops_curated = {
      name        = "${local.name_prefix}-curated-data"
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
      database_name = "${local.name_prefix}-raw-data"
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
      database_name = "${local.name_prefix}-raw-data"
      description   = "Crawler for raw ML data"
      schedule      = "cron(0 2 * * ? *)"  # Daily at 2 AM
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
      database_name = "${local.name_prefix}-curated-data"
      description   = "Crawler for curated ML data"
      schedule      = "cron(0 3 * * ? *)"  # Daily at 3 AM
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
      ruleset = jsonencode([
        {
          Name = "Completeness"
          Rules = [
            "ColumnCount > 0",
            "IsComplete \"feature_1\"",
            "IsComplete \"feature_2\"",
            "IsComplete \"target\""
          ]
        },
        {
          Name = "Validity"
          Rules = [
            "ColumnDataType \"feature_1\" = \"NUMERIC\"",
            "ColumnDataType \"feature_2\" = \"NUMERIC\"",
            "ColumnDataType \"target\" = \"NUMERIC\""
          ]
        }
      ])
      target_table = {
        database_name = "${local.name_prefix}-raw-data"
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