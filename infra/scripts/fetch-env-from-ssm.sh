#!/usr/bin/env bash
# Fetch app env vars from AWS SSM Parameter Store (path /ai/app/) and write ~/.env.
# Run on EC2 (uses instance IAM role). Usage: ./fetch-env-from-ssm.sh [output_file]
# Default output_file is ~/.env.

set -e
# Use instance region if AWS region not set (required for AWS CLI on EC2)
if [[ -z "${AWS_DEFAULT_REGION:-}" && -z "${AWS_REGION:-}" ]]; then
  export AWS_DEFAULT_REGION=$(curl -s -m 2 "${INSTANCE_METADATA_URL}/latest/dynamic/instance-identity/document" | grep -o '"region" : "[^"]*"' | cut -d'"' -f4) || true
fi
[[ -z "${AWS_DEFAULT_REGION:-}" ]] && export AWS_DEFAULT_REGION="${AWS_REGION:-ap-south-1}"

OUTPUT="${1:-$HOME/.env}"
# SSM path must match Terraform (leading slash; trailing slash for path prefix)
PATH_PREFIX="/ai/app"

# Get parameters by path; output "Name\tValue" per line (path with trailing slash for prefix)
TMP_ERR=$(mktemp)
RAW=$(aws ssm get-parameters-by-path \
  --path "$PATH_PREFIX/" \
  --recursive \
  --with-decryption \
  --query 'Parameters[*].[Name,Value]' \
  --output text 2>"$TMP_ERR") || true

if [[ -n "$(cat "$TMP_ERR")" ]]; then
  echo "AWS SSM error:" >&2
  cat "$TMP_ERR" >&2
  rm -f "$TMP_ERR"
  exit 1
fi
rm -f "$TMP_ERR"

if [[ -z "$RAW" ]]; then
  echo "No parameters under $PATH_PREFIX/ (check IAM and that Terraform created them)." >&2
  exit 1
fi

# Write KEY=VALUE (strip path prefix from Name; Name is e.g. /ai/app/OPENAI_API_KEY)
while IFS=$'\t' read -r name value; do
  key="${name#$PATH_PREFIX/}"
  printf '%s=%s\n' "$key" "$value"
done <<< "$RAW" > "$OUTPUT"

echo "Wrote $(wc -l < "$OUTPUT") env vars to $OUTPUT"
