# İzleme ve Paneller (Opsiyonel)

Bu VPS kurulumunda sistem sadeleştirilmiştir ve monitoring (Prometheus, Grafana) varsayılan olarak kapalıdır. İhtiyaç halinde kolayca açıp kapatabilirsiniz.

Monitoring’i etkinleştir:

```bash
cd ~/freehekim-rag-api
docker compose -f deployment/docker/docker-compose.server.yml \
               -f deployment/docker/docker-compose.monitoring.yml up -d
```

Monitoring’i durdur (yalnızca izleme servisleri):

```bash
docker stop docker-grafana-1 docker-prometheus-1 docker-alertmanager-1 2>/dev/null || true
docker rm   docker-grafana-1 docker-prometheus-1 docker-alertmanager-1 2>/dev/null || true
```

## Prometheus
- Scrape: API → `/metrics`, Qdrant → `/metrics`
- Örnek config: `deployment/monitoring/prometheus.yml`

## Alert Kuralları
Alert kuralları otomatik olarak yüklenir: `deployment/monitoring/alerts/rag-api-alerts.yml`

**Mevcut Alertler:**
- `RagApiDown` (critical): API 2 dakikadan fazla down
- `HighErrorRate` (critical): 5xx hata oranı >5% (5dk)
- `HighResponseTime` (warning): P95 gecikme >2s (5dk)
- `HighMemoryUsage` (warning): RAM kullanımı >80%
- `HighCPUUsage` (warning): CPU kullanımı >80% (2dk)
- `QdrantDown` (critical): Qdrant 2 dakikadan fazla down

**Alert Kontrolü:**
```bash
# Alert kurallarını görüntüle
curl http://localhost:9090/api/v1/rules

# Aktif alertleri kontrol et
curl http://localhost:9090/api/v1/alerts
```

## Grafana
- Datasource: Prometheus (deployment/monitoring/grafana-datasources.yml)
- Dashboard import:
  - `deployment/monitoring/grafana-dashboards/rag-overview.json`
  - `deployment/monitoring/grafana-dashboards/qdrant-overview.json`

## Erişim Katmanı: Cloudflare Access + WAF
- metrics subdomain sadece uygulama metrikleri içindir: `metrics.hakancloud.com -> http://localhost:8080`
- Uygulama metrik endpoint’i: `/metrics` (FastAPI Instrumentator)
- Cloudflare Access: `metrics.hakancloud.com` için oturum zorunlu
- WAF (önerilir): yalnızca `/metrics` yoluna izin ver
  - İfade: `(http.host eq "metrics.hakancloud.com") and (http.request.uri.path ne "/metrics")`
  - Aksiyon: `Block`
- Beklenen sonuçlar:
  - `curl -I https://metrics.hakancloud.com/metrics` → `302` (Access login)
  - `curl -I https://metrics.hakancloud.com/random` → `403` (WAF)

## RAG Metrikleri
- `rag_total_seconds` (Histogram)
- `rag_embed_seconds` (Histogram)
- `rag_search_seconds{collection}` (Histogram)
- `rag_generate_seconds` (Histogram)
- `rag_errors_total{type}` (Counter)
 - `rag_tokens_total{model}` (Counter)

## Örnek Sorgular (PromQL)
- İstek hızı: `rate(http_requests_total[1m])`
- API gecikme p95: `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))`
- RAG toplam p95: `histogram_quantile(0.95, sum by (le) (rate(rag_total_seconds_bucket[5m])))`
## Hafif İzleme (Workers/cron veya Systemd user)

- Bu VPS’te üçüncü parti olmadan hafif kontrol kullanılıyor: `deployment/scripts/health_monitor.sh` + systemd `--user` timer.
- Varsayılan olarak 2 dakikada bir `https://rag.hakancloud.com/health` ve `http://127.0.0.1:8080/ready` kontrol edilir.
- Slack/Telegram uyarıları için sunucu kullanıcı env dosyasına aşağıyı ekleyin:

```env
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/XXX/YYY/ZZZ
ALERT_TELEGRAM_BOT_TOKEN=123456:ABCDEF
ALERT_TELEGRAM_CHAT_ID=123456
```

- Zamanlayıcı durumu:

```bash
systemctl --user list-timers | grep freehekim-health-monitor
```

### İleri Özellikler
- Art arda N hata → uyarı (false‑positive filtresi):
  - `MONITOR_CONSECUTIVE_FAILS=3` (varsayılan 3)
- Sessiz saatler (gece uyarılarını bastırma):
  - `MONITOR_QUIET_START=23:00`
  - `MONITOR_QUIET_END=07:00`
  - `MONITOR_SUPPRESS_ALERTS_DURING_QUIET=true` (varsayılan true)
- Kurtarma bildirimi:
  - `MONITOR_SEND_RECOVERY=true` (varsayılan true)
