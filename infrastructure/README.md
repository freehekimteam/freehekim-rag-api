# Infrastructure

Infrastructure as Code (IaC) for FreeHekim RAG API.

## Overview

This directory contains all infrastructure provisioning and configuration management code:

```
infrastructure/
├── terraform/      # Infrastructure provisioning (Hetzner, Cloudflare)
├── ansible/        # Configuration management
├── cloudflare/     # Cloudflare Tunnel configuration
└── README.md       # This file
```

## Components

### 1. Terraform - Infrastructure Provisioning

Provisions cloud infrastructure:
- ✅ Hetzner Cloud servers
- ✅ Networking & firewalls
- ✅ DNS records
- ✅ Load balancers (future)

**See:** [`terraform/README.md`](terraform/README.md)

### 2. Ansible - Configuration Management

Configures and manages servers:
- ✅ System updates & security
- ✅ Docker installation
- ✅ Application deployment
- ✅ Monitoring setup

**See:** [`ansible/README.md`](ansible/README.md)

### 3. Cloudflare - Secure Access

Zero Trust network access:
- ✅ Cloudflare Tunnel
- ✅ DDoS protection
- ✅ SSL/TLS termination
- ✅ Access policies

**See:** [`cloudflare/README.md`](cloudflare/README.md)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLOUDFLARE                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  DNS        │  │  CDN/WAF     │  │  Zero Trust      │  │
│  │  Management │  │  Protection  │  │  Access          │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ Cloudflare Tunnel
                         │ (secure, no exposed ports)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              HETZNER CLOUD SERVER                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Docker Host (Ubuntu 24.04)                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │ FastAPI     │  │ Qdrant      │  │ Monitoring  │  │  │
│  │  │ (Port 8080) │  │ (Port 6333) │  │ (9090/3000) │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Managed by: Terraform + Ansible                           │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

1. **Tools:**
   ```bash
   # Install Terraform
   brew install terraform  # or apt/yum

   # Install Ansible
   pip install ansible

   # Install cloudflared
   brew install cloudflared  # or wget binary
   ```

2. **Accounts:**
   - Hetzner Cloud account + API token
   - Cloudflare account + API token
   - Domain managed by Cloudflare

3. **SSH Keys:**
   ```bash
   ssh-keygen -t rsa -b 4096 -C "freehekim-deploy"
   ```

### Deployment Flow

```
1. Terraform (Provision)
   └─> Create server, firewall, network

2. Ansible (Configure)
   └─> Install Docker, setup security, deploy app

3. Cloudflare (Connect)
   └─> Setup tunnel, configure DNS

4. Verify
   └─> Test endpoints, check monitoring
```

### Step-by-Step

#### 1. Provision Infrastructure (Terraform)

```bash
cd infrastructure/terraform

# Configure
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars

# Deploy
terraform init
terraform plan
terraform apply

# Get server IP
terraform output server_ip
```

#### 2. Configure Server (Ansible)

```bash
cd ../ansible

# Update inventory with server IP
vim inventory.yml

# Test connection
ansible all -i inventory.yml -m ping

# Configure server
ansible-playbook -i inventory.yml playbook.yml
```

#### 3. Setup Cloudflare Tunnel

```bash
cd ../cloudflare

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create freehekim-rag

# Configure
cp tunnel-config.yml /etc/cloudflared/config.yml
# Edit with tunnel ID

# Route DNS
cloudflared tunnel route dns freehekim-rag rag.hakancloud.com

# Install service
cloudflared service install
systemctl start cloudflared
```

#### 4. Deploy Application

```bash
# SSH to server
ssh freehekim@<server_ip>

# Clone repo
git clone https://github.com/freehekimteam/freehekim-rag-api.git
cd freehekim-rag-api

# Setup environment
cp .env.example .env
vim .env

# Deploy
cd deployment/docker
docker-compose -f docker-compose.server.yml up -d
```

#### 5. Verify

```bash
# Health check (local)
curl http://localhost:8080/health

# Health check (through tunnel)
curl https://rag.hakancloud.com/health

# Check metrics
curl https://rag.hakancloud.com/metrics
```

## Infrastructure Cost

### Current Setup (Hetzner CX22)

```
Monthly Costs:
├─ Server (CX22): ~€6/month
│  └─ 2 vCPU, 4GB RAM, 40GB SSD
├─ Backups: ~€1/month
├─ Traffic: Included (20TB)
└─ Cloudflare: FREE

Total: ~€7/month
```

### Scaling Options

| Type | vCPU | RAM | Disk | Price/month | Use Case |
|------|------|-----|------|-------------|----------|
| CX22 | 2 | 4GB | 40GB | €6 | Development |
| CX32 | 4 | 8GB | 80GB | €12 | Production |
| CX42 | 8 | 16GB | 160GB | €24 | High Traffic |

## Security

### Network Security

- ✅ No exposed ports (Cloudflare Tunnel)
- ✅ UFW firewall configured
- ✅ fail2ban for SSH protection
- ✅ Cloudflare DDoS protection
- ✅ Zero Trust access policies

### Application Security

- ✅ Environment variables for secrets
- ✅ Docker secrets management
- ✅ Regular security updates
- ✅ SSL/TLS encryption
- ✅ API rate limiting

### Compliance

- ✅ KVKK/GDPR compliant
- ✅ No personal data storage
- ✅ Audit logging
- ✅ Access control

## Monitoring

### Metrics (Prometheus)

- API response time
- Request rate & errors
- System resources (CPU, RAM, Disk)
- Container health

### Logs

- Application logs (JSON format)
- System logs (journalctl)
- Access logs (nginx/traefik)
- Audit logs

### Alerts

- High error rate (>1%)
- High response time (>1s)
- Low disk space (<10%)
- Container down

## Backup & Disaster Recovery

### Backup Strategy

```
Automated Backups (daily @ 2 AM):
├─ Qdrant vector database
├─ Application configuration
├─ Environment files
└─ Monitoring data

Retention: 14 days
Storage: Hetzner Object Storage
```

### Recovery Plan

```
RTO (Recovery Time Objective): 1 hour
RPO (Recovery Point Objective): 24 hours

Steps:
1. Provision new server (Terraform)
2. Configure server (Ansible)
3. Restore data from backup
4. Update DNS/Tunnel
5. Verify functionality
```

## Troubleshooting

### Common Issues

```bash
# Terraform fails
terraform refresh
terraform plan

# Ansible connection fails
ansible all -i inventory.yml -m ping -vvv

# Cloudflare tunnel down
systemctl status cloudflared
journalctl -u cloudflared -f

# Server not responding
ssh freehekim@<server_ip>
docker ps
docker logs freehekim-rag-api
```

## Development vs Production

### Development

```bash
# Local Docker Compose
cd deployment/docker
docker-compose up

# Access directly
curl http://localhost:8080/health
```

### Production

```bash
# Terraform + Ansible + Cloudflare
terraform apply
ansible-playbook playbook.yml
cloudflared tunnel run

# Access through tunnel
curl https://rag.hakancloud.com/health
```

## Documentation

- [Terraform Docs](terraform/README.md)
- [Ansible Docs](ansible/README.md)
- [Cloudflare Docs](cloudflare/README.md)
- [Deployment Docs](../deployment/README.md)

## Support

- **Infrastructure Issues:** Check server logs, Cloudflare dashboard
- **Application Issues:** Check application logs, metrics
- **Security Concerns:** security@hakancloud.com

---

⚖️ **Infrastructure as Code - Version Controlled, Reproducible, Auditable**
