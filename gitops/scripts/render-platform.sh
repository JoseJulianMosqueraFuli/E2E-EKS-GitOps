#!/usr/bin/env sh
set -eu
: "${AWS_ACCOUNT_ID:?AWS_ACCOUNT_ID is required in the ArgoCD platform configuration}"
: "${AWS_REGION:?AWS_REGION is required in the ArgoCD platform configuration}"
case "$AWS_ACCOUNT_ID" in *[!0-9]*|'') echo "Invalid AWS account ID" >&2; exit 1 ;; esac
[ "${#AWS_ACCOUNT_ID}" -eq 12 ] && [ "$AWS_ACCOUNT_ID" != 000000000000 ] || { echo "A configured AWS account is required" >&2; exit 1; }
printf '%s' "$AWS_REGION" | grep -Eq '^[a-z]{2}(-[a-z]+)+-[0-9]+$' || { echo "Invalid AWS region" >&2; exit 1; }
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
printf 'AWS_ACCOUNT_ID=%s\nAWS_REGION=%s\n' "$AWS_ACCOUNT_ID" "$AWS_REGION" > "$SCRIPT_DIR/../platform/aws.env"
kustomize build .
