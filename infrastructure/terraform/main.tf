# FreeHekim RAG API - Terraform Infrastructure
# Hetzner Cloud + Cloudflare configuration

terraform {
  required_version = ">= 1.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }

  # Backend configuration for state management
  backend "local" {
    path = "terraform.tfstate"
  }
}

# Variables
variable "hcloud_token" {
  description = "Hetzner Cloud API Token"
  type        = string
  sensitive   = true
}

variable "cloudflare_api_token" {
  description = "Cloudflare API Token"
  type        = string
  sensitive   = true
}

variable "server_name" {
  description = "Server name"
  type        = string
  default     = "freehekim-rag-production"
}

variable "server_type" {
  description = "Hetzner server type"
  type        = string
  default     = "cx22"  # 2 vCPU, 4GB RAM, 40GB SSD
}

variable "server_location" {
  description = "Server location"
  type        = string
  default     = "fsn1"  # Falkenstein, Germany
}

# Providers
provider "hcloud" {
  token = var.hcloud_token
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# SSH Key
resource "hcloud_ssh_key" "default" {
  name       = "freehekim-deploy-key"
  public_key = file("~/.ssh/id_rsa.pub")
}

# Server
resource "hcloud_server" "rag_api" {
  name        = var.server_name
  server_type = var.server_type
  location    = var.server_location
  image       = "ubuntu-24.04"

  ssh_keys = [hcloud_ssh_key.default.id]

  labels = {
    environment = "production"
    project     = "freehekim-rag"
    managed_by  = "terraform"
  }

  user_data = file("${path.module}/cloud-init.yaml")
}

# Firewall
resource "hcloud_firewall" "rag_api" {
  name = "freehekim-rag-firewall"

  # SSH (only from specific IPs in production)
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = [
      "0.0.0.0/0",      # TODO: Restrict to specific IPs
      "::/0"
    ]
  }

  # HTTP/HTTPS (Cloudflare Tunnel handles this internally)
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
  }
}

# Attach firewall to server
resource "hcloud_firewall_attachment" "rag_api" {
  firewall_id = hcloud_firewall.rag_api.id
  server_ids  = [hcloud_server.rag_api.id]
}

# Outputs
output "server_ip" {
  description = "Server public IP address"
  value       = hcloud_server.rag_api.ipv4_address
}

output "server_id" {
  description = "Server ID"
  value       = hcloud_server.rag_api.id
}

output "server_status" {
  description = "Server status"
  value       = hcloud_server.rag_api.status
}
