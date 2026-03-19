output "state_bucket_name" {
  description = "S3 bucket name for Terraform state"
  value       = aws_s3_bucket.tf_state.id
}

output "lock_table_name" {
  description = "DynamoDB table name for state lock"
  value       = aws_dynamodb_table.tf_lock.name
}

output "aws_region" {
  description = "AWS region used"
  value       = var.aws_region
}
