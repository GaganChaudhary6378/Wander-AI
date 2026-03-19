# Main Terraform: EC2 instance, key pair, security group, Elastic IP.
# Requires bootstrap to be applied first. Configure backend in backend.tf.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

# Latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# Key pair: use verifact-key public key (copy ~/.ssh/verifact-key.pub to infra/main/verifact-key.pub or set public_key_path)
resource "aws_key_pair" "verifact" {
  key_name   = "verifact-key"
  public_key = var.public_key
}

# SSM Parameter Store: one parameter per app env var (path /ai/app/<KEY>)
resource "aws_ssm_parameter" "app_env" {
  for_each = toset(var.app_env_keys)

  name        = "/ai/app/${each.key}"
  type        = "SecureString"
  value       = var.app_env[each.key]
  description = "App env var ${each.key} for ai"

  tags = {
    Project = "ai"
  }
}

# IAM role for EC2: allow reading SSM parameters under /ai/app/
resource "aws_iam_role" "app" {
  name = "ai-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = { Project = "ai" }
}

resource "aws_iam_role_policy" "app_ssm" {
  name = "ai-app-ssm"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParametersByPath", "ssm:GetParameters", "ssm:GetParameter"]
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/ai/app/*"
    }]
  })
}

resource "aws_iam_instance_profile" "app" {
  name = "ai-app-profile"
  role = aws_iam_role.app.name
}

# Security group: SSH + Streamlit (WanderAI / agentic-travel-main)
resource "aws_security_group" "app" {
  name        = "ai-app-sg"
  description = "SSH and app ports for ai EC2"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Streamlit (WanderAI)"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "ai-app-sg"
    Project = "ai"
  }
}

# Install Docker script (used in user_data)
locals {
  install_docker_script = file("${path.module}/../scripts/install-docker.sh")
}

# EC2 instance with Docker installed via user_data
resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.verifact.key_name
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name
  user_data              = local.install_docker_script
  user_data_replace_on_change = true

  root_block_device {
    volume_size = var.root_volume_size_gb
    volume_type = "gp3"
  }

  tags = {
    Name    = "ai-app"
    Project = "ai"
  }
}

# Elastic IP attached to the instance
resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = {
    Name    = "ai-app-eip"
    Project = "ai"
  }
}
