# Monitoring Configuration

This directory contains Prometheus and Grafana configuration files for FreeHekim RAG API monitoring.

**✅ All configs are in the repo** - No manual copying needed!

## Deployment Instructions

### 1. Create data directories (first time only)

```bash
# On server
mkdir -p ~/data/prometheus ~/data/grafana

# Set permissions for Grafana
sudo chown -R 472:472 ~/data/grafana
```

### 2. Start monitoring stack

```bash
cd ~/freehekim-rag-api

# Start API + Monitoring together
docker compose -f deployment/docker/docker-compose.server.yml \
               -f deployment/docker/docker-compose.monitoring.yml up -d

# Or restart if already running
docker compose -f deployment/docker/docker-compose.server.yml \
               -f deployment/docker/docker-compose.monitoring.yml restart prometheus grafana
```

### 3. Access dashboards

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000
  - Default credentials: `admin` / `hakancloud2025`
  - Change password on first login

**Note:** Datasource is auto-configured via `grafana-datasources.yml`

### 4. Check alert rules

```bash
# View loaded alerts
curl http://localhost:9090/api/v1/rules

# Check alert status
curl http://localhost:9090/api/v1/alerts
```

Alerts are defined in `alerts/rag-api-alerts.yml` and automatically loaded.

## Available Metrics

### API Metrics (from FastAPI Instrumentator)

- `http_requests_total` - Total request count
- `http_request_duration_seconds` - Request latency histogram
- `http_request_duration_seconds_sum` - Total request time
- `http_request_duration_seconds_count` - Request count (for rate calculation)

### Custom Metrics (RAG)

Uygulama aşağıdaki özel metrikleri yayımlar:

- `rag_total_seconds` (Histogram): Tüm RAG pipeline süresi
- `rag_embed_seconds` (Histogram): Embedding süresi
- `rag_search_seconds{collection}` (Histogram): Arama süresi (internal/external)
- `rag_generate_seconds` (Histogram): LLM üretim süresi
- `rag_errors_total{type}` (Counter): Hata sayacı (embedding/database/rag/unexpected)

## Grafana Dashboard Queries

### Request Rate (per minute)
```promql
rate(http_requests_total[1m])
```

### Avg Response Time
```promql
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

### Error Rate
```promql
rate(http_requests_total{status=~"5.."}[5m])
```

### 95th Percentile Latency
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

## Alerting (Optional)

Add alert rules to `prometheus.yml`:

```yaml
rule_files:
  - "alerts/api_alerts.yml"
```

Example alert (`alerts/api_alerts.yml`):

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests/sec"
```

## Backup

Prometheus data is stored in `~/data/prometheus` - backup regularly:

```bash
# Create backup
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz ~/data/prometheus

# Restore
tar -xzf prometheus-backup-YYYYMMDD.tar.gz -C ~/data/
```

## Troubleshooting

### Prometheus not scraping API

```bash
# Check if API metrics endpoint is accessible
curl http://localhost:8080/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets
```

### Grafana permission denied

```bash
# Fix ownership
sudo chown -R 472:472 ~/data/grafana
```

## Resources

- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/)
- [FastAPI Instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator)
