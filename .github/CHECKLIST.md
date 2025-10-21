# FreeHekim RAG API - Deployment Checklist

Use this checklist to ensure smooth deployment and avoid missing critical steps.

---

## Phase 1: Repository Rename & Setup

### GitHub Repository Configuration

- [ ] **Rename repository**
  - Go to: Settings → General → Repository name
  - Change: `hakancloud-core` → `freehekim-rag-api`
  - Confirm rename

- [ ] **Update local git remote**
  ```bash
  git remote set-url origin https://github.com/freehekimteam/freehekim-rag-api.git
  git remote -v  # Verify
  ```

- [ ] **Configure GitHub Secrets**
  - Navigate to: Settings → Secrets and variables → Actions
  - Add repository secrets:
    - `HC_SSH_HOST` = Your server IP or hostname
    - `HC_SSH_USER` = SSH username (e.g., `freehekim`)
    - `HC_SSH_KEY` = SSH private key (Ed25519 recommended)

- [ ] **Create GitHub Environments**
  - Navigate to: Settings → Environments
  - Create `staging` environment (no protection rules)
  - Create `production` environment (enable required reviewers)

- [ ] **Configure GitHub Actions Permissions**
  - Settings → Actions → General → Workflow permissions
  - Enable: "Read and write permissions"
  - Enable: "Allow GitHub Actions to create and approve pull requests"

---

## Phase 2: Server Preparation

### Server Directory Structure

SSH into your Hetzner server:

- [ ] **Create base directories**
  ```bash
  mkdir -p ~/freehekim-rag-api
  mkdir -p ~/.hakancloud
  mkdir -p ~/data/prometheus
  mkdir -p ~/data/grafana
  mkdir -p ~/apps/hakancloud-ops/monitoring
  ```

- [ ] **Clone repository**
  ```bash
  cd ~/freehekim-rag-api
  git clone https://github.com/freehekimteam/freehekim-rag-api.git .
  git checkout dev
  ```

### Environment Configuration

- [ ] **Create `.env` file**
  ```bash
  nano ~/.hakancloud/.env
  ```

- [ ] **Fill in required variables** (see `.env.example`)
  - [ ] `QDRANT_HOST` - Qdrant server hostname
  - [ ] `QDRANT_PORT` - 443 (HTTPS) or 6333 (HTTP)
  - [ ] `QDRANT_API_KEY` - Qdrant API key
  - [ ] `OPENAI_API_KEY` - OpenAI API key (starts with `sk-proj-`)
  - [ ] `OPENAI_EMBEDDING_MODEL` - `text-embedding-3-small`
  - [ ] `EMBED_PROVIDER` - `openai`
  - [ ] `ENV` - `staging` or `production`

- [ ] **Secure environment file**
  ```bash
  chmod 600 ~/.hakancloud/.env
  ```

- [ ] **Verify environment file**
  ```bash
  cat ~/.hakancloud/.env  # Should show all variables
  ```

### Docker Installation

- [ ] **Install Docker** (if not already installed)
  ```bash
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  ```

- [ ] **Add user to docker group**
  ```bash
  sudo usermod -aG docker $USER
  ```

- [ ] **Logout and login again** (for group change to take effect)

- [ ] **Verify Docker installation**
  ```bash
  docker --version
  docker compose version
  ```

### Monitoring Setup (Optional but Recommended)

- [ ] **Copy monitoring configs**
  ```bash
  cp ~/freehekim-rag-api/monitoring/prometheus.yml \
     ~/apps/hakancloud-ops/monitoring/

  cp ~/freehekim-rag-api/monitoring/grafana-datasources.yml \
     ~/apps/hakancloud-ops/monitoring/
  ```

- [ ] **Fix Grafana permissions**
  ```bash
  sudo chown -R 472:472 ~/data/grafana
  ```

---

## Phase 3: Initial Deployment

### Manual First Deployment

- [ ] **Login to GitHub Container Registry**
  ```bash
  echo "YOUR_GITHUB_PAT" | docker login ghcr.io -u YOUR_USERNAME --password-stdin
  ```

- [ ] **Pull Docker images**
  ```bash
  cd ~/freehekim-rag-api
  docker compose -f docker/docker-compose.server.yml pull
  ```

- [ ] **Start services**
  ```bash
  docker compose -f docker/docker-compose.server.yml up -d
  ```

- [ ] **Check service status**
  ```bash
  docker compose -f docker/docker-compose.server.yml ps
  ```

### Health Verification

- [ ] **API health check**
  ```bash
  curl http://127.0.0.1:8080/health
  # Expected: {"status":"ok","env":"staging"}
  ```

- [ ] **Qdrant readiness check**
  ```bash
  curl http://127.0.0.1:8080/ready
  # Expected: {"ready":true,"qdrant":{"connected":true,...}}
  ```

- [ ] **Check API logs**
  ```bash
  docker compose -f docker/docker-compose.server.yml logs -f api
  # Should show: Uvicorn running on http://0.0.0.0:8080
  ```

- [ ] **Check Qdrant logs**
  ```bash
  docker compose -f docker/docker-compose.server.yml logs qdrant
  # Should show: Qdrant started
  ```

### Test RAG Pipeline

- [ ] **Test RAG query endpoint**
  ```bash
  curl -X POST http://127.0.0.1:8080/rag/query \
    -H "Content-Type: application/json" \
    -d '{"q": "Test soru"}'
  ```

- [ ] **Verify OpenAI API key works**
  - Check logs for successful embedding generation
  - Should NOT see "OPENAI_API_KEY not configured" error

- [ ] **Verify Qdrant collections exist**
  ```bash
  curl http://127.0.0.1:6333/collections
  # Should list: freehekim_internal, freehekim_external
  ```

---

## Phase 4: GitHub Actions Testing

### Test CI Workflow

- [ ] **Push a small change to dev branch**
  ```bash
  git commit --allow-empty -m "test: trigger CI"
  git push origin dev
  ```

- [ ] **Monitor GitHub Actions**
  - Go to: Actions tab in GitHub
  - Watch CI workflow run
  - Verify all steps pass (lint, test)

### Test Staging Deployment

- [ ] **Verify deploy-staging workflow triggered**
  - Should trigger automatically after CI passes
  - Check Actions tab for "deploy-staging" run

- [ ] **Monitor deployment logs**
  - Watch SSH deployment step
  - Verify health check passes

- [ ] **Verify new image deployed**
  ```bash
  # On server
  docker images | grep freehekim-rag-api
  # Should show :dev tag with recent timestamp
  ```

- [ ] **Recheck health endpoints**
  ```bash
  curl http://127.0.0.1:8080/health
  curl http://127.0.0.1:8080/ready
  ```

---

## Phase 5: Monitoring Setup (If Using)

### Start Monitoring Stack

- [ ] **Start Prometheus + Grafana**
  ```bash
  docker compose -f docker/docker-compose.server.yml \
                 -f docker/docker-compose.monitoring.yml up -d
  ```

- [ ] **Verify monitoring containers running**
  ```bash
  docker ps | grep -E "prometheus|grafana"
  ```

### Access Monitoring Dashboards

- [ ] **Port forward Prometheus** (from local machine)
  ```bash
  ssh -L 9090:localhost:9090 freehekim@YOUR_SERVER_IP
  ```

- [ ] **Open Prometheus UI**
  - Browser: http://localhost:9090
  - Check Status → Targets
  - Verify `hakancloud-api` and `qdrant` are UP

- [ ] **Port forward Grafana** (from local machine)
  ```bash
  ssh -L 3000:localhost:3000 freehekim@YOUR_SERVER_IP
  ```

- [ ] **Configure Grafana**
  - Browser: http://localhost:3000
  - Login: `admin` / `hakancloud2025`
  - **Change password immediately!**
  - Verify Prometheus datasource is connected

---

## Phase 6: Production Deployment (When Ready)

### Pre-Production Checklist

- [ ] **Staging has been stable for 48+ hours**
- [ ] **All tests are passing**
- [ ] **Monitoring shows no errors**
- [ ] **Backup of Qdrant data created**
- [ ] **Rollback plan documented**

### Production Tag & Deploy

- [ ] **Create production tag**
  ```bash
  git tag v1.0.0
  git push origin v1.0.0
  ```

- [ ] **Monitor deploy-prod workflow**
  - Watch Actions tab
  - Approve deployment if required reviewers enabled

- [ ] **Verify production deployment**
  ```bash
  # On server
  docker images | grep freehekim-rag-api
  # Should show :prod tag
  ```

### Post-Deployment Verification

- [ ] **Health check (production)**
  ```bash
  curl http://127.0.0.1:8080/health
  # Expected: {"status":"ok","env":"production"}
  ```

- [ ] **Load test** (use tool like `ab` or `wrk`)
  ```bash
  # Example with Apache Bench
  ab -n 100 -c 10 http://127.0.0.1:8080/health
  ```

- [ ] **Monitor for 1 hour**
  - Watch Grafana dashboards
  - Check error rates
  - Verify response times < 2s

---

## Phase 7: Ongoing Maintenance

### Daily Checks

- [ ] **Check service status**
  ```bash
  docker compose -f docker/docker-compose.server.yml ps
  ```

- [ ] **Review logs for errors**
  ```bash
  docker compose logs --tail=100 api | grep -i error
  ```

### Weekly Checks

- [ ] **Check disk usage**
  ```bash
  df -h
  du -sh /var/lib/qdrant_data
  ```

- [ ] **Review Grafana dashboards**
  - Request rates
  - Error rates
  - Token usage (cost monitoring)

- [ ] **Backup Qdrant data**
  ```bash
  tar -czf qdrant-backup-$(date +%Y%m%d).tar.gz /var/lib/qdrant_data
  ```

### Monthly Checks

- [ ] **Update Docker images**
  ```bash
  docker compose pull
  docker compose up -d
  ```

- [ ] **Rotate secrets** (every 90 days)
  - [ ] Generate new SSH key
  - [ ] Update GitHub Secret
  - [ ] Remove old key from server

- [ ] **Review security logs**
  ```bash
  sudo journalctl -u docker -n 1000 | grep -i auth
  ```

---

## Troubleshooting Reference

### Common Issues

**Issue: GitHub Actions "Permission denied (publickey)"**
- Solution: Verify `HC_SSH_KEY` secret contains full private key
- Verify public key is in `~/.ssh/authorized_keys` on server

**Issue: API returns 503 on /ready**
- Solution: Check Qdrant is running: `docker ps | grep qdrant`
- Check Qdrant logs: `docker logs freehekim-rag-api-qdrant-1`

**Issue: "OPENAI_API_KEY not configured"**
- Solution: Verify `.env` file exists: `cat ~/.hakancloud/.env`
- Verify API key starts with `sk-proj-`
- Restart API: `docker compose restart api`

**Issue: Docker "Cannot connect to the Docker daemon"**
- Solution: Check Docker is running: `sudo systemctl status docker`
- Verify user in docker group: `groups $USER`
- Logout and login again

---

## Emergency Rollback Procedure

If production deployment fails:

1. **Stop current services**
   ```bash
   docker compose -f docker/docker-compose.server.yml down
   ```

2. **Switch to previous version**
   ```bash
   export IMAGE_TAG=v1.0.0-previous
   docker compose -f docker/docker-compose.server.yml pull
   docker compose -f docker/docker-compose.server.yml up -d
   ```

3. **Verify health**
   ```bash
   curl http://127.0.0.1:8080/health
   ```

4. **Notify team & investigate**

---

## Sign-Off

When all checklist items are complete:

- [ ] **Documentation reviewed**
- [ ] **Team notified of deployment**
- [ ] **Monitoring alerts configured**
- [ ] **Backup schedule verified**
- [ ] **Runbook created for common issues**

**Deployed by:** ___________
**Date:** ___________
**Version:** ___________

---

**Maintained by:** Codex - FreeHekim Official DevOps
**Last Updated:** 2025-10-16
