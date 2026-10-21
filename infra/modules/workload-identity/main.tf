locals {
  workloads = {
    mlflow = {
      subject = "system:serviceaccount:mlflow:${var.environment}-mlflow"
      buckets = [var.bucket_arns.model_artifacts]
    }
    argo = {
      subject = "system:serviceaccount:argo-workflows:argo-workflow"
      buckets = [var.bucket_arns.raw_data, var.bucket_arns.curated_data, var.bucket_arns.model_artifacts]
    }
    secrets = {
      subject = "system:serviceaccount:mlflow:${var.environment}-mlflow-secrets"
      buckets = []
    }
    backup = {
      subject = "system:serviceaccount:mlflow:${var.environment}-mlflow-backup-sa"
      buckets = [var.bucket_arns.backups]
    }
  }
}

data "aws_iam_policy_document" "trust" {
  for_each = local.workloads
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:sub"
      values   = [each.value.subject]
    }
    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "workload" {
  for_each           = local.workloads
  name               = "${var.name_prefix}-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.trust[each.key].json
  tags               = var.tags
}

data "aws_iam_policy_document" "storage" {
  for_each = { for name, workload in local.workloads : name => workload if length(workload.buckets) > 0 }
  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = each.value.buckets
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
    resources = [for bucket in each.value.buckets : "${bucket}/${each.key == "backup" ? "mlflow-backups/*" : "*"}"]
  }
  statement {
    actions   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "storage" {
  for_each = data.aws_iam_policy_document.storage
  name     = "platform-storage"
  role     = aws_iam_role.workload[each.key].id
  policy   = data.aws_iam_policy_document.storage[each.key].json
}

data "aws_iam_policy_document" "inference_images" {
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"
    ]
    resources = [var.inference_repository_arn]
  }
}

resource "aws_iam_role_policy" "inference_images" {
  name   = "inference-images"
  role   = aws_iam_role.workload["argo"].id
  policy = data.aws_iam_policy_document.inference_images.json
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = ["arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:mlops/${var.environment == "prod" ? "production" : var.environment}/mlflow/*"]
  }
  statement {
    actions   = ["kms:Decrypt"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "secrets" {
  name   = "mlflow-secret-values"
  role   = aws_iam_role.workload["secrets"].id
  policy = data.aws_iam_policy_document.secrets.json
}
