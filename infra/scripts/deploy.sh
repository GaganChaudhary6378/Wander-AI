#!/usr/bin/env bash
# Build images, push to Docker Hub, copy docker-compose to EC2, and deploy.
# Usage: ./deploy.sh <tagname> [ec2_host]
#   tagname   - e.g. latest, v1.0.0 (used for gagan-*:tagname)
#   ec2_host  - ec2-user@<elastic-ip> (default: read from terraform output if available)
#
# Prereqs: docker login, SSH key ~/.ssh/verifact-key, terraform output for public_ip

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_DIR="${COMPOSE_DIR:-$REPO_ROOT/agentic-travel-main}"
DEPLOY_COMPOSE="$SCRIPT_DIR/../docker-compose.deploy.yml"

TAG="${1:?Usage: $0 <tagname> [ec2_host]}"
EC2_HOST="${2:-}"

if [[ -z "$EC2_HOST" ]]; then
  if command -v terraform &>/dev/null; then
    MAIN_DIR="$(cd "$SCRIPT_DIR/../main" && pwd)"
    if [[ -d "$MAIN_DIR" ]] && [[ -f "$MAIN_DIR/terraform.tfstate" || -n "${TF_STATE:-}" ]]; then
      EC2_IP=$(terraform -chdir="$MAIN_DIR" output -raw public_ip 2>/dev/null || true)
      if [[ -n "$EC2_IP" ]]; then
        EC2_HOST="ec2-user@$EC2_IP"
      fi
    fi
  fi
  if [[ -z "$EC2_HOST" ]]; then
    echo "EC2 host not set. Pass as second argument: $0 $TAG ec2-user@<elastic-ip>"
    exit 1
  fi
fi

echo "=== Build and push images (tag=$TAG) ==="
cd "$COMPOSE_DIR"
# EC2 is x86_64; build for linux/amd64 so manifest matches
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker compose build

# Single image: WanderAI (agentic-travel-main). Compose image name = <project>_<service> or <project>-<service>
PROJECT="${COMPOSE_DIR##*/}"
docker tag "${PROJECT}-app:latest" "gagan:$TAG"
docker push "gagan:$TAG"

echo "=== Copy docker-compose and deploy on EC2 ==="
if [[ ! -f "$DEPLOY_COMPOSE" ]]; then
  echo "Missing $DEPLOY_COMPOSE"
  exit 1
fi

# Substitute TAG in compose and copy to EC2
if command -v envsubst &>/dev/null; then
  TAG="$TAG" envsubst '${TAG}' < "$DEPLOY_COMPOSE" > /tmp/docker-compose.deploy.yml
else
  sed "s/\${TAG}/$TAG/g" "$DEPLOY_COMPOSE" > /tmp/docker-compose.deploy.yml
fi
scp -i ~/.ssh/verifact-key -o StrictHostKeyChecking=accept-new /tmp/docker-compose.deploy.yml "$EC2_HOST:~/docker-compose.yml"

# Copy and run script that fetches env from Parameter Store into ~/.env
FETCH_ENV_SCRIPT="$SCRIPT_DIR/fetch-env-from-ssm.sh"
scp -i ~/.ssh/verifact-key "$FETCH_ENV_SCRIPT" "$EC2_HOST:~/fetch-env-from-ssm.sh"
ssh -i ~/.ssh/verifact-key "$EC2_HOST" "chmod +x ~/fetch-env-from-ssm.sh && ~/fetch-env-from-ssm.sh && cd ~ && docker compose -f docker-compose.yml pull && docker compose -f docker-compose.yml up -d --remove-orphans"

echo "=== Deploy done. WanderAI (Streamlit) at http://${EC2_HOST#*@}:8501 ==="
