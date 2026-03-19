#!/bin/bash
# Install Docker on Amazon Linux 2. Used as EC2 user_data.

set -e
yum update -y
yum install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# Docker Compose v2 (plugin)
mkdir -p /usr/local/lib/docker/cli-plugins
curl -sSL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Ensure ec2-user can use docker after first login (current boot already has group)
# Next login will have docker group; for user_data scripts running as root, docker is available.
