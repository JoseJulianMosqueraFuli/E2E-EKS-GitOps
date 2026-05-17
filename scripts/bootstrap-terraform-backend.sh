#!/bin/bash
set -euo pipefail

# Bootstrap Terraform Remote Backend on AWS
# Run this ONCE per AWS account to set up the S3 + DynamoDB backend.
# After running, uncomment the backend block in infra/environments/<env>/main.tf

ENV=${1:-dev}
REGION=${2:-us-west-2}
BUCKET_NAME="mlops-terraform-state-${ENV}"
DYNAMO_TABLE="mlops-terraform-locks-${ENV}"
KMS_ALIAS="alias/mlops-${ENV}-key"

echo "=== Bootstrapping Terraform backend for environment: ${ENV} ==="

# Create S3 bucket for state
echo "Creating S3 bucket: ${BUCKET_NAME}..."
aws s3api create-bucket \
  --bucket "${BUCKET_NAME}" \
  --region "${REGION}" \
  --create-bucket-configuration LocationConstraint="${REGION}" 2>/dev/null || echo "Bucket may already exist"

aws s3api put-bucket-versioning \
  --bucket "${BUCKET_NAME}" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "${BUCKET_NAME}" \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "aws:kms"
        },
        "BucketKeyEnabled": true
      }
    ]
  }'

aws s3api put-public-access-block \
  --bucket "${BUCKET_NAME}" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Create DynamoDB table for locking
echo "Creating DynamoDB table: ${DYNAMO_TABLE}..."
aws dynamodb create-table \
  --table-name "${DYNAMO_TABLE}" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "${REGION}" 2>/dev/null || echo "Table may already exist"

# Create KMS key (or use existing)
echo "KMS key should be created by Terraform or manually."
echo "If you already have one, update the backend block in main.tf with its ARN."

echo ""
echo "=== Bootstrap complete ==="
echo "Next steps:"
echo "  1. Uncomment the backend block in infra/environments/${ENV}/main.tf"
echo "  2. Run: cd infra/environments/${ENV} && terraform init"
