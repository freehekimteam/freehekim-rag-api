# Deployment Guide for FreeHekim RAG API

This guide covers GitHub Actions setup, secrets configuration, and deployment procedures.

---

## Prerequisites

- GitHub repository admin access
- SSH access to Hetzner server
- OpenAI API key
- Qdrant instance (cloud or self-hosted)

---

## 1. GitHub Secrets Configuration

### Required Secrets

Navigate to: **Repository → Settings → Secrets and variables → Actions**

#### **Repository Secrets**

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `HC_SSH_HOST` | Hetzner server IP or hostname | Server dashboard or `curl ifconfig.me` |
| `HC_SSH_USER` | SSH username (e.g., `freehekim`) | Your server user account |
| `HC_SSH_KEY` | SSH private key for authentication | Generate new deploy key (see below) |

#### **Generating SSH Deploy Key**

```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/freehekim-deploy

# Copy private key (paste this into HC_SSH_KEY secret)
cat ~/.ssh/freehekim-deploy

# Copy public key to server
ssh-copy-id -i ~/.ssh/freehekim-deploy.pub freehekim@YOUR_SERVER_IP

# Test connection
ssh -i ~/.ssh/freehekim-deploy freehekim@YOUR_SERVER_IP
```

**Security Note:** The private key should ONLY be stored in GitHub Secrets. Never commit it.

---

### Environment Secrets

Create two environments in **Settings → Environments:**

#### **Staging Environment**

- Name: `staging`
- Protection rules: None (auto-deploy on push to `dev`)
- Secrets: Same as repository secrets (inherited)

#### **Production Environment**

- Name: `production`
- Protection rules: **Required reviewers** (recommended)
- Secrets: Same as repository secrets (inherited)

**Why separate environments?**
- Different approval workflows
- Separate deployment logs
- Environment-specific URLs in the future

---

## 2. Server Setup

SSH into your Hetzner server and run:

```bash
# 1. Create directory structure
mkdir -p ~/freehekim-rag-api
mkdir -p ~/.hakancloud
mkdir -p ~/data/prometheus ~/data/grafana
mkdir -p ~/apps/hakancloud-ops/monitoring

# 2. Clone repository
cd ~/freehekim-rag-api
git clone https://github.com/freehekimteam/freehekim-rag-api.git .
git checkout dev

# 3. Create environment file
cat > ~/.hakancloud/.env <<EOF
# Environment
ENV=staging

# Qdrant Configuration
QDRANT_HOST=rag.hakancloud.com
QDRANT_PORT=443
QDRANT_API_KEY=your_qdrant_api_key_here

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...your_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Embedding Provider
EMBED_PROVIDER=openai

# API Configuration
API_PORT=8080
API_HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
EOF

# 4. Secure the environment file
chmod 600 ~/.hakancloud/.env

# 5. Copy monitoring configs (if using monitoring stack)
cp monitoring/prometheus.yml ~/apps/hakancloud-ops/monitoring/
cp monitoring/grafana-datasources.yml ~/apps/hakancloud-ops/monitoring/

# 6. Fix Grafana permissions
sudo chown -R 472:472 ~/data/grafana

# 7. Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 8. Log out and back in for Docker group to take effect
exit
```

---

## 3. Manual Deployment (First Time)

```bash
# Login to GitHub Container Registry
echo "YOUR_GITHUB_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Pull images
cd ~/freehekim-rag-api
docker compose -f docker/docker-compose.server.yml pull

# Start services
docker compose -f docker/docker-compose.server.yml up -d

# Check logs
docker compose -f docker/docker-compose.server.yml logs -f

# Verify health
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/ready
```

---

## 4. Automated Deployment (GitHub Actions)

### Staging Deployment

**Trigger:** Push to `dev` branch

```bash
git add .
git commit -m "feat: new feature"
git push origin dev
```

GitHub Actions will:
1. Run tests (CI)
2. Build Docker image → `ghcr.io/freehekimteam/freehekim-rag-api:dev`
3. Push to GitHub Container Registry
4. SSH to server
5. Pull latest image
6. Restart services
7. Run health check

**Check status:**
- GitHub Actions tab → Latest workflow run
- Server: `docker compose -f docker/docker-compose.server.yml ps`

---

### Production Deployment

**Trigger:** Create and push a tag

```bash
# Create semantic version tag
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will:
1. Build production image → `ghcr.io/freehekimteam/freehekim-rag-api:prod`
2. Wait for approval (if configured)
3. Deploy to production
4. Run extensive health checks

**Rollback:**
```bash
# On server
cd ~/freehekim-rag-api
docker compose -f docker/docker-compose.server.yml down
export IMAGE_TAG=v1.0.0-previous  # Previous working version
docker compose -f docker/docker-compose.server.yml up -d
```

---

## 5. Monitoring Setup (Optional)

### Start Monitoring Stack

```bash
cd ~/freehekim-rag-api

# Start API + Qdrant + Prometheus + Grafana
docker compose -f docker/docker-compose.server.yml \
               -f docker/docker-compose.monitoring.yml up -d
```

### Access Dashboards

**Prometheus:**
```bash
# Port forward to local machine
ssh -L 9090:localhost:9090 freehekim@YOUR_SERVER_IP

# Open in browser
http://localhost:9090
```

**Grafana:**
```bash
# Port forward
ssh -L 3000:localhost:3000 freehekim@YOUR_SERVER_IP

# Open in browser
http://localhost:3000

# Default credentials
Username: admin
Password: hakancloud2025
```

**Important:** Change Grafana password on first login!

---

## 6. Troubleshooting

### GitHub Actions Fails

**Error: "Permission denied (publickey)"**
```bash
# Check HC_SSH_KEY secret is correct
# Verify public key is in server's authorized_keys:
cat ~/.ssh/authorized_keys
```

**Error: "docker login failed"**
```bash
# Check GITHUB_TOKEN permissions
# Repository Settings → Actions → General → Workflow permissions
# Enable "Read and write permissions"
```

### Health Check Fails

**API returns 503:**
```bash
# Check API logs
docker logs freehekim-rag-api-api-1

# Common issues:
# 1. Environment variables not set
cat ~/.hakancloud/.env

# 2. Qdrant not reachable
curl http://localhost:6333/collections

# 3. OpenAI API key invalid
# Check API key in .env
```

**Qdrant Connection Refused:**
```bash
# Check Qdrant is running
docker ps | grep qdrant

# Check Qdrant logs
docker logs freehekim-rag-api-qdrant-1

# Restart Qdrant
docker compose -f docker/docker-compose.server.yml restart qdrant
```

### Monitoring Not Working

**Prometheus can't scrape API:**
```bash
# Check if metrics endpoint is accessible from Prometheus container
docker exec freehekim-rag-api-prometheus-1 curl http://api:8080/metrics

# If fails, check network
docker network inspect freehekim-rag-api_hakancloud
```

**Grafana permission denied:**
```bash
# Fix ownership
sudo chown -R 472:472 ~/data/grafana

# Restart Grafana
docker compose -f docker/docker-compose.monitoring.yml restart grafana
```

---

## 7. Maintenance

### Updating Dependencies

```bash
# On server
cd ~/freehekim-rag-api
git pull origin dev

# Rebuild and restart
docker compose -f docker/docker-compose.server.yml up -d --build
```

### Viewing Logs

```bash
# All services
docker compose -f docker/docker-compose.server.yml logs -f

# Specific service
docker compose -f docker/docker-compose.server.yml logs -f api

# Last 100 lines
docker compose -f docker/docker-compose.server.yml logs --tail=100 api
```

### Backup Qdrant Data

```bash
# Create backup
tar -czf qdrant-backup-$(date +%Y%m%d).tar.gz /var/lib/qdrant_data

# Transfer to local machine
scp freehekim@YOUR_SERVER_IP:~/qdrant-backup-*.tar.gz ./backups/
```

### Rotating Secrets (Every 90 Days)

1. Generate new SSH key
2. Add to server's `authorized_keys`
3. Update `HC_SSH_KEY` in GitHub Secrets
4. Remove old key from server
5. Rotate `.env` API keys if needed

---

## 8. Security Checklist

- [ ] SSH key is Ed25519 (not RSA)
- [ ] Private key is ONLY in GitHub Secrets
- [ ] `.env` file has `chmod 600` permissions
- [ ] Grafana default password changed
- [ ] GitHub Actions has minimal permissions
- [ ] Qdrant API key is strong (32+ chars)
- [ ] All services bind to `127.0.0.1` only
- [ ] Cloudflare Tunnel configured (if public access needed)
- [ ] Backup rotation is automated

---

## 9. Cost Monitoring

**OpenAI Usage:**
```bash
# Check metrics endpoint
curl http://localhost:8080/metrics | grep rag_tokens

# Or view in Grafana dashboard
```

**Server Resources:**
```bash
# Check Docker resource usage
docker stats

# Check disk usage
df -h
du -sh /var/lib/qdrant_data
```

---

## 10. Emergency Contacts

- **DevOps Issues:** Codex (this AI assistant)
- **Security Issues:** security@hakancloud.com
- **Infrastructure:** Hetzner support

---

## Quick Reference

**Start services:**
```bash
docker compose -f docker/docker-compose.server.yml up -d
```

**Stop services:**
```bash
docker compose -f docker/docker-compose.server.yml down
```

**View logs:**
```bash
docker compose -f docker/docker-compose.server.yml logs -f api
```

**Check health:**
```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/ready
```

**Update from GitHub:**
```bash
cd ~/freehekim-rag-api
git pull origin dev
docker compose -f docker/docker-compose.server.yml pull
docker compose -f docker/docker-compose.server.yml up -d
```

---

**Last Updated:** 2025-10-16
**Maintained By:** Codex - FreeHekim Official DevOps
