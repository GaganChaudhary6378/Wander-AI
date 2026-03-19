variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "public_key" {
  description = "Contents of the public key for verifact-key (e.g. from file(\"$HOME/.ssh/verifact-key.pub\") or copy to verifact-key.pub)"
  type        = string
  sensitive   = true
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "root_volume_size_gb" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20
}

# App env vars stored in Parameter Store; EC2 fetches them at deploy time.
# Keys list is non-sensitive so for_each can use it; values stay in app_env (sensitive).
variable "app_env_keys" {
  description = "List of env var names (must match keys in app_env)"
  type        = list(string)
  default     = []
}

variable "app_env" {
  description = "Map of env var name to value; stored in SSM Parameter Store under /ai-league/app/"
  type        = map(string)
  default     = {}
  sensitive   = true
}
