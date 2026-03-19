# Remote backend: use after bootstrap has been applied.
# Initialize with:
#   terraform init -backend-config=backend.hcl
# Or copy backend.hcl.example to backend.hcl and fill in bucket + key + dynamodb_table.

terraform {
  backend "s3" {
    # bucket, key, region, dynamodb_table set via -backend-config or backend.hcl
  }
}
