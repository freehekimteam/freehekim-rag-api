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

### 1. Setup Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your credentials
vim .env
```

### 2. Deploy with Docker Compose

```bash
# Production deployment
cd deployment/docker
docker-compose -f docker-compose.server.yml up -d

# With monitoring
docker-compose -f docker-compose.server.yml \
               -f docker-compose.monitoring.yml up -d
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

## Backup & Recovery

### Backup

```bash
# Run backup script
./scripts/backup.sh

# Manual backup
docker exec qdrant tar czf /backup/qdrant-$(date +%Y%m%d).tar.gz /qdrant/storage
```

### Restore

```bash
# Stop services
docker-compose down

# Restore data
tar xzf backup.tar.gz -C /

# Start services
docker-compose up -d
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
