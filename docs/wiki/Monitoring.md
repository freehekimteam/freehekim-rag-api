# İzleme ve Paneller

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
