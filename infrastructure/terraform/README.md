# Terraform Infrastructure

Infrastructure as Code for FreeHekim RAG API using Terraform.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.0
- Hetzner Cloud account & API token
- Cloudflare account & API token
- SSH key pair

## Setup

### 1. Install Terraform

```bash
# macOS
brew install terraform

# Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

### 2. Create `terraform.tfvars`

```bash
# DO NOT commit this file!
cat > terraform.tfvars <<EOF
hcloud_token          = "your-hetzner-api-token"
cloudflare_api_token  = "your-cloudflare-api-token"
server_name           = "freehekim-rag-production"
server_type           = "cx22"
server_location       = "fsn1"
EOF
```

### 3. Initialize Terraform

```bash
terraform init
```

### 4. Plan Infrastructure

```bash
terraform plan
```

### 5. Apply Infrastructure

```bash
terraform apply
```

## Server Types

| Type | vCPU | RAM | Disk | Price/month |
|------|------|-----|------|-------------|
| cx22 | 2 | 4GB | 40GB | ~€6 |
| cx32 | 4 | 8GB | 80GB | ~€12 |
| cx42 | 8 | 16GB | 160GB | ~€24 |

## Locations

- `fsn1` - Falkenstein, Germany (EU)
- `nbg1` - Nuremberg, Germany (EU)
- `hel1` - Helsinki, Finland (EU)

## Outputs

After apply, you'll get:

```bash
server_ip     = "X.X.X.X"
server_id     = "12345678"
server_status = "running"
```

## SSH Access

```bash
ssh freehekim@<server_ip>
```

## Destroy Infrastructure

```bash
terraform destroy
```

## State Management

Currently using local backend. For team collaboration, consider:

- Terraform Cloud
- S3 + DynamoDB
- Consul
- GitLab Managed Terraform State

## Security Notes

- ⚠️ Never commit `terraform.tfvars`
- ⚠️ Never commit `terraform.tfstate`
- ✅ Use `.gitignore` to exclude sensitive files
- ✅ Restrict SSH access by IP in production
- ✅ Enable automatic security updates

## Next Steps

1. Setup Ansible for configuration management
2. Configure Cloudflare Tunnel
3. Deploy application with Docker Compose
4. Setup monitoring (Prometheus/Grafana)
