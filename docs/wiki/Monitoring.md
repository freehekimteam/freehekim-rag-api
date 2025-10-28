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
## Alertmanager Bildirimleri (Önerilen)

- Kurumsal bildirim akışı Prometheus → Alertmanager zinciri ile yönetilir.
- Telegram için alıcıyı `deployment/monitoring/alertmanager.yml` içinde tanımlayın:

```yaml
route:
  group_by: [alertname]
  group_wait: 2m
  group_interval: 30m
  repeat_interval: 4h
  receiver: telegram

receivers:
  - name: telegram
    telegram_configs:
      - bot_token: "<BOT_TOKEN>"
        chat_id: <CHAT_ID>
        send_resolved: false
```

- Notlar:
  - Kullanılan Alertmanager sürümünde `--config.expand-env` desteklenmeyebilir; bu nedenle gizli bilgileri doğrudan konfig dosyasına veya host tarafında güvenli bir kopyaya (/etc/freehekim-rag/alertmanager.yml) yazın ve compose ile mount edin.
  - “Quiet hours” için UI’dan “Silences” kullanmanız önerilir (örn. 00:00–08:00 arası). Alternatif olarak child route üzerinde `active_time_intervals` tanımlanabilir.

- Servisi yeniden başlatın (systemd üzerinden):

```bash
sudo systemctl restart freehekim-rag.service
```

### Quiet Hours (UI ile Silence ekleme)

Gece saatlerinde (ör. 00:00–08:00) geçici olarak uyarıları susturmak için Alertmanager UI üzerinden Silence oluşturabilirsiniz:

1) UI’yi açın: `http://127.0.0.1:9093`
2) “Silences” sekmesine gidin → “New Silence”
3) Matchers (örneklerden birini seçin; aşırı genel kurallardan kaçının):
   - Sadece kritik ve uyarı: `severity=~"(warning|critical)"`
   - Sadece API down: `alertname="RagApiDown"`
4) Zaman aralığı: Başlangıç `00:00`, Bitiş `08:00` (yerel saat). Tek seferlik sessizliktir.
5) Comment: “Quiet hours (00:00–08:00) – ops”
6) Create Silence

Komutla (API) Silence oluşturma örneği:

```bash
curl -X POST http://127.0.0.1:9093/api/v2/silences \
  -H 'Content-Type: application/json' \
  -d '{
        "matchers": [
          {"name": "severity", "value": "(warning|critical)", "isRegex": true}
        ],
        "startsAt": "2025-01-01T00:00:00+03:00",
        "endsAt":   "2025-01-01T08:00:00+03:00",
        "createdBy": "ops",
        "comment":   "Quiet hours (00:00–08:00)"
      }'
```

Aktif silenceları görüntüleme:

```bash
curl -s http://127.0.0.1:9093/api/v2/silences | jq '.[].{id: .id, matchers: .matchers, startsAt, endsAt, comment}'
```

Notlar
- Tekrarlayan (her gün) “quiet hours” için en iyi yaklaşım, Alertmanager konfigürasyonuna zaman aralığı (time_intervals) ekleyip ilgili child route’ta `active_time_intervals` kullanmaktır. UI’daki Silence tek seferliktir.

## Opsiyonel: Hafif İzleme (Systemd user)

- Alternatif hafif kontrol betiği: `deployment/scripts/health_monitor.sh` (varsayılan devre dışı).
- Yalnızca özel durumlarda önerilir. Alertmanager ile birlikte kullanmayın (çift bildirim olur).

Zamanlayıcıyı etkinleştirmek (opsiyonel):

```bash
systemctl --user enable --now freehekim-health-monitor.timer
systemctl --user list-timers | grep freehekim-health-monitor
```
