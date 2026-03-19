# Wander AI — Infrastructure (Terraform + Deploy)

Deploy the app to AWS EC2 with Terraform: bootstrap state storage, then EC2 + Elastic IP, key pair `verifact-key`, Docker install via user_data, **app env vars in SSM Parameter Store**, and a deploy script that builds/pushes images and runs docker-compose on the instance.

## Prerequisites

- AWS CLI configured (credentials and region)
- Terraform >= 1.0
- Docker (for building and pushing images)
- SSH key pair: `~/.ssh/verifact-key` and `~/.ssh/verifact-key.pub`

## 1. Bootstrap (once per account/region)

Creates S3 bucket for Terraform state and DynamoDB table for state locking.

```bash
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set state_bucket_name (globally unique) and lock_table_name
terraform init
terraform apply
```

Note the outputs: `state_bucket_name`, `lock_table_name`, `aws_region`. You will use them in the main backend config.

## 2. Main Terraform (EC2, key pair, security group, Elastic IP)

### Backend config

```bash
cd infra/main
cp backend.hcl.example backend.hcl
# Edit backend.hcl with values from bootstrap output:
#   bucket, key, region, dynamodb_table
```

### Public key for `verifact-key`

Provide the **contents** of your public key so Terraform can create the key pair in AWS. Either:

- **Option A:** Copy the key into the repo (do not commit if the repo is public):
  ```bash
  cp ~/.ssh/verifact-key.pub infra/main/verifact-key.pub
  ```
  Then in `infra/main` create a `terraform.tfvars`:
  ```hcl
  public_key = file("${path.module}/verifact-key.pub")
  ```
  Or pass at apply time (see Option B without copying the file).

- **Option B:** Pass the key when running Terraform (no file in repo):
  ```bash
  export TF_VAR_public_key="$(cat ~/.ssh/verifact-key.pub)"
  terraform apply
  ```

### App env vars (Parameter Store)

App environment variables (e.g. from `agentic-travel-main/.env`) are stored in **AWS Systems Manager Parameter Store** under the path `/ai/app/<KEY>`. The EC2 instance has an IAM role that can read these; at deploy time, `fetch-env-from-ssm.sh` writes them to `~/.env` on the EC2 for docker-compose.

In `infra/main/terraform.tfvars` (do not commit), set a map of env names to values:

```hcl
app_env = {
  "OPENAI_API_KEY"         = "sk-..."
  "SERPAPI_API_KEY"        = "..."
  "GOOGLE_PLACES_API_KEY"  = "..."
  # ... (see terraform.tfvars.example for full list)
  "DEMO_MODE"              = "auto"
  "LLM_PROVIDER"           = "openai"
  "LLM_MODEL"              = "gpt-4o-mini"
}
```

Terraform will create SSM parameters (SecureString) for each key. You can add or change parameters later and re-apply; the deploy script always fetches the latest from Parameter Store before starting containers.

### Apply

```bash
cd infra/main
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

After apply, note `public_ip` and `ssh_command`. The instance has Docker and Docker Compose installed via user_data.

## 3. Install-Docker script

The EC2 instance uses `infra/scripts/install-docker.sh` as **user_data**. It installs Docker and Docker Compose (plugin) and adds `ec2-user` to the `docker` group. No separate run is needed.

## 4. Deploy script (build, push, copy compose, deploy on EC2)

When you want to deploy a new version:

1. **Log in to Docker Hub** (for pushing):
   ```bash
   docker login
   ```

2. **Run the deploy script** with a tag name and optional EC2 host:
   ```bash
   ./infra/scripts/deploy.sh <tagname> [ec2_user@<elastic-ip>]
   ```
   Example:
   ```bash
   ./infra/scripts/deploy.sh v1.0.0
   ```
   If you omit the second argument, the script tries to get `public_ip` from `infra/main` Terraform output and uses `ec2-user@<public_ip>`.

The script:

- Builds the image from `agentic-travel-main` (WanderAI — Streamlit + LangGraph) or `COMPOSE_DIR` if set.
- Tags and pushes `gagan:<tagname>`.
- Copies `infra/docker-compose.deploy.yml` (with `TAG` substituted) to the EC2.
- Copies and runs `fetch-env-from-ssm.sh` on the EC2 to pull env vars from Parameter Store into `~/.env`.
- SSHs to the EC2 and runs `docker compose pull && docker compose up -d --remove-orphans`.

Ensure `~/.ssh/verifact-key` is the private key for the instance. Env vars are supplied from **Parameter Store** (see “App env vars” above); do not copy `.env` from your machine. The app (WanderAI) is a single Streamlit service on port **8501**.

## 5. Elastic IP

Elastic IP is created and attached to the EC2 instance in `infra/main/main.tf` (`aws_eip.app`). The same IP is used for SSH and for the app (e.g. gRPC on port 50051).

## Layout

```
infra/
├── README.md                 # This file
├── bootstrap/
│   ├── main.tf               # S3 state bucket + DynamoDB lock
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── main/
│   ├── main.tf               # EC2, key pair, SG (port 8501), EIP, IAM, SSM params
│   ├── backend.tf            # S3 backend (config via backend.hcl)
│   ├── backend.hcl.example
│   ├── variables.tf
│   └── outputs.tf
├── scripts/
│   ├── install-docker.sh     # EC2 user_data
│   ├── fetch-env-from-ssm.sh  # Fetches Parameter Store → ~/.env on EC2
│   └── deploy.sh             # Build, push, copy compose, fetch env, deploy
└── docker-compose.deploy.yml # Production compose (image: + ${TAG})
```
