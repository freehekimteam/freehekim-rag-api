# Deployment

Production deployment configurations for FreeHekim RAG API.

## Directory Structure

```
deployment/
├── docker/           # Docker & Docker Compose configs
├── monitoring/       # Prometheus & Grafana configs
├── scripts/          # Deployment & maintenance scripts
└── README.md         # This file
```

## Quick Deploy

### 1. Setup Environment (system-wide .env)

```bash
sudo mkdir -p /etc/freehekim-rag
sudo cp .env.example /etc/freehekim-rag/.env
sudo chgrp ragsvc /etc/freehekim-rag/.env 2>/dev/null || true
sudo chmod 640 /etc/freehekim-rag/.env

# IMPORTANT: Never commit real secrets. Keep /etc/freehekim-rag/.env out of the repo.

# Recommended production values (edit /etc/freehekim-rag/.env):
# ENV=production
# QDRANT_HOST=localhost
# QDRANT_PORT=6333
# QDRANT__SERVICE__API_KEY=<server_api_key>   # enables auth on Qdrant REST
# QDRANT_API_KEY=<client_api_key>             # used by API to talk to Qdrant
# OPENAI_API_KEY=sk-...
# REQUIRE_API_KEY=true
# API_KEY=<strong_random_value>
```

### 2. Provision and Systemd Service (Recommended)

```bash
sudo bash deployment/scripts/provision_freehekim_rag.sh
sudo systemctl start freehekim-rag.service
sudo systemctl enable freehekim-rag.service
```

### 3. Verify

```bash
# Check containers
docker ps

# Check logs
docker logs freehekim-rag-api

# Test health endpoint
curl http://localhost:8080/health
```

## Components

### Docker

See [`docker/README.md`](docker/README.md) for:
- Dockerfile optimization
- Multi-stage builds
- Docker Compose configuration
- Container networking

### Monitoring

See [`monitoring/README.md`](monitoring/README.md) for:
- Prometheus metrics
- Grafana dashboards
- Alert rules
- Log aggregation

### Scripts

See [`scripts/README.md`](scripts/README.md) for:
- Deployment automation
- Backup scripts
- Health checks
- Maintenance tasks

## Deployment Strategies

### Blue-Green Deployment

```bash
# Deploy new version (green)
docker-compose -p freehekim-rag-green up -d

# Test green
curl http://localhost:8081/health

# Switch traffic (update nginx/cloudflare)
# ...

# Remove old version (blue)
docker-compose -p freehekim-rag-blue down
```

### Rolling Updates

```bash
# Update with zero downtime
docker-compose up -d --no-deps --build api
```

### Canary Deployment

```bash
# Deploy canary (10% traffic)
docker-compose up -d --scale api=2

# Monitor metrics
# ...

# Full rollout
docker-compose up -d --scale api=10
```

## Security Checklist

- [ ] Environment variables configured
- [ ] Secrets not in version control
- [ ] Firewall configured (UFW)
- [ ] fail2ban enabled
- [ ] SSL/TLS certificates valid
- [ ] Cloudflare Tunnel configured
- [ ] Regular backups enabled
- [ ] Monitoring alerts configured

### Legacy/External Vars

- HC_ENV → ENV (uygulama `HC_ENV`’i de kabul eder ama `ENV` tercih edin)
- HC_CF_TUNNEL_HOST → health monitor için dış adres; `MONITOR_URL_HEALTH` yoksa otomatik türetilir
- CF_API_TOKEN, CF_ZONE → altyapı otomasyonu (Terraform/Cloudflare), uygulama .env’ine koymayın
- IMAGE_TAG → imaj etiketi; `/etc/freehekim-rag/.env` veya systemd override ile belirleyin
- LANG → sistem locale ihtiyacı varsa ayarlayın

## Rollback

### Docker Compose

```bash
# Stop current version
docker-compose down

# Deploy previous version
git checkout v1.0.0
docker-compose up -d
```

### Container Registry

```bash
# Pull previous image
docker pull ghcr.io/freehekimteam/freehekim-rag-api:v1.0.0

# Restart with old image
docker-compose up -d
```

## Monitoring

### Logs

```bash
# Application logs
docker logs -f freehekim-rag-api

# All services
docker-compose logs -f

# Specific service
docker-compose logs -f prometheus
```

### Metrics

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### Alerts

Configured in `monitoring/prometheus.yml`:
- High error rate
- High response time
- Low disk space
- Container down

## Backup & Recovery (Daily Incremental)

```bash
# Status
systemctl status freehekim-rag-backup.timer

# Manual run
sudo systemctl start freehekim-rag-backup.service

# Check
tail -n 50 /var/backups/freehekim-rag/backup.log
```

Restore from latest backup:

```bash
sudo systemctl stop freehekim-rag.service
sudo rsync -a --delete /var/backups/freehekim-rag/latest/qdrant/ /srv/qdrant/
sudo rsync -a --delete /var/backups/freehekim-rag/latest/etc/ /etc/freehekim-rag/
sudo systemctl start freehekim-rag.service
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs freehekim-rag-api

# Check resources
docker stats

# Recreate container
docker-compose up -d --force-recreate
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Restart container
docker-compose restart api

# Scale down if needed
docker-compose up -d --scale api=1
```

### Network Issues

```bash
# Check network
docker network ls
docker network inspect freehekim-rag_default

# Recreate network
docker-compose down
docker-compose up -d
```

## CI/CD Integration

### GitHub Actions (self‑hosted runner)

- Bu repo, yerel runner üzerinde çalışan 2 otomatik iş ile gelir:
  - `Deploy (manual)`: Bir tıkla docker compose pull/up
  - `Release (on tag)`: `v*.*.*` etiketi push edilince compose pull/up
- Kurulum: Settings → Actions → Runners → New self‑hosted runner (Linux). Hızlı kurulum için `/tmp/gha-runner`, kalıcı servis için `/opt/actions-runner` kullanabilirsiniz.
- Çalıştırma: Actions → `Deploy (manual)` → `Run workflow`.

#### Örnek yerel runner kurulumu (özet)

```bash
# Üretim sunucusunda (production makinenizde) normal kullanıcıyla çalışın (ör. freehekim)
mkdir -p ~/actions-runner && cd ~/actions-runner

# En güncel sürümü indir (Linux x64)
curl -fsSL -o runner.tar.gz "https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64-$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | grep tag_name | cut -d '"' -f4 | sed 's/^v//').tar.gz"
tar xzf runner.tar.gz

# Runner'ı repo ile ilişkilendir (GitHub → Settings → Actions → Runners → New self‑hosted runner → token)
./config.sh --url https://github.com/<owner>/<repo> --token <RUNNER_TOKEN> --labels linux,self-hosted --name prod-runner

# Servis olarak kur ve başlat
sudo ./svc.sh install
sudo ./svc.sh start

# Docker yetkileri (gerekirse)
sudo usermod -aG docker "$USER"
newgrp docker
```

Runner hesabının `docker` grubunda olduğundan ve `~/.config/freehekim-rag/.env` dosyasının bulunduğundan emin olun. Workflow’lar production ortamı ile işaretlenmiştir (`environment: production`).

### GitLab CI

```yaml
# .gitlab-ci.yml
deploy:
  script:
    - scp deployment/docker/docker-compose.server.yml server:/app/
    - ssh server 'cd /app && docker-compose up -d'
```

## Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
