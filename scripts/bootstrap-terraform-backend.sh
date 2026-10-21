#!/usr/bin/env bash
set -euo pipefail
ENVIRONMENT="${1:-dev}"
REGION="${2:-${AWS_REGION:?Pass the AWS region as the second argument or AWS_REGION}}"
case "$ENVIRONMENT" in dev|staging|prod) ;; *) echo "Environment must be dev, staging or prod" >&2; exit 1 ;; esac
export AWS_DEFAULT_REGION="$REGION"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
[[ "$ACCOUNT_ID" =~ ^[0-9]{12}$ ]] || { echo "Invalid AWS account" >&2; exit 1; }
BUCKET_NAME="mlops-terraform-state-${ENVIRONMENT}-${ACCOUNT_ID}-${REGION}"
DYNAMO_TABLE="mlops-terraform-locks-${ENVIRONMENT}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_FILE="$ROOT/infra/environments/$ENVIRONMENT/backend.hcl"
if ! aws s3api head-bucket --bucket "$BUCKET_NAME" --expected-bucket-owner "$ACCOUNT_ID" 2>/dev/null; then
  if [ "$REGION" = us-east-1 ]; then
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION" --create-bucket-configuration "LocationConstraint=$REGION"
  fi
fi
aws s3api put-bucket-versioning --bucket "$BUCKET_NAME" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET_NAME" --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"},"BucketKeyEnabled":true}]}'
aws s3api put-public-access-block --bucket "$BUCKET_NAME" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
policy="$(mktemp)"
trap 'rm -f "$policy"' EXIT
cat > "$policy" <<EOF
{"Version":"2012-10-17","Statement":[{"Sid":"DenyInsecureTransport","Effect":"Deny","Principal":"*","Action":"s3:*","Resource":["arn:aws:s3:::$BUCKET_NAME","arn:aws:s3:::$BUCKET_NAME/*"],"Condition":{"Bool":{"aws:SecureTransport":"false"}}}]}
EOF
aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy "file://$policy"
if ! aws dynamodb describe-table --table-name "$DYNAMO_TABLE" >/dev/null 2>&1; then
  aws dynamodb create-table --table-name "$DYNAMO_TABLE" --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --sse-specification Enabled=true
fi
aws dynamodb wait table-exists --table-name "$DYNAMO_TABLE"
umask 077
cat > "$BACKEND_FILE" <<EOF
bucket = "$BUCKET_NAME"
key = "$ENVIRONMENT/terraform.tfstate"
region = "$REGION"
dynamodb_table = "$DYNAMO_TABLE"
encrypt = true
EOF
echo "Backend prepared. Review $BACKEND_FILE, then initialize explicitly:"
echo "terraform -chdir=infra/environments/$ENVIRONMENT init -backend-config=backend.hcl"
echo "If local state already exists, review the migration and add -migrate-state."
