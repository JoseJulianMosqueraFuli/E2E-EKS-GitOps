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
    # region = "us-west-2"
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

# ECR Repositories
resource "aws_ecr_repository" "trainer" {
  name                 = "${local.name_prefix}-trainer"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "inference" {
  name                 = "${local.name_prefix}-inference"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}