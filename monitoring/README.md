# Monitoring Configuration

This directory contains Prometheus and Grafana configuration files for HakanCloud Core monitoring.

## Deployment Instructions

### 1. Copy configs to server

```bash
# On your server
mkdir -p ~/apps/hakancloud-ops/monitoring

# Copy configs
scp monitoring/prometheus.yml server:~/apps/hakancloud-ops/monitoring/
scp monitoring/grafana-datasources.yml server:~/apps/hakancloud-ops/monitoring/
```

### 2. Create data directories

```bash
# On server
mkdir -p ~/data/prometheus ~/data/grafana

# Set permissions for Grafana
sudo chown -R 472:472 ~/data/grafana
```

### 3. Start monitoring stack

```bash
cd ~/hakancloud-core

# Start with monitoring
docker compose -f docker/docker-compose.server.yml \
               -f docker/docker-compose.monitoring.yml up -d
```

### 4. Access dashboards

- **Prometheus:** http://localhost:9090 (port-forward if remote)
- **Grafana:** http://localhost:3000
  - Default credentials: `admin` / `hakancloud2025`
  - Change password on first login

## Available Metrics

### API Metrics (from FastAPI Instrumentator)

- `http_requests_total` - Total request count
- `http_request_duration_seconds` - Request latency histogram
- `http_request_duration_seconds_sum` - Total request time
- `http_request_duration_seconds_count` - Request count (for rate calculation)

### Custom Metrics (to be added)

```python
from prometheus_client import Counter, Histogram

rag_queries_total = Counter('rag_queries_total', 'Total RAG queries')
rag_query_duration = Histogram('rag_query_duration_seconds', 'RAG query duration')
rag_tokens_used = Counter('rag_tokens_used_total', 'Total OpenAI tokens used')
```

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
