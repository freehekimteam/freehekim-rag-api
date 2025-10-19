# İzleme ve Paneller

## Prometheus
- Scrape: API → `/metrics`, Qdrant → `/metrics`
- Örnek config: `deployment/monitoring/prometheus.yml`

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

## Örnek Sorgular (PromQL)
- İstek hızı: `rate(http_requests_total[1m])`
- API gecikme p95: `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))`
- RAG toplam p95: `histogram_quantile(0.95, sum by (le) (rate(rag_total_seconds_bucket[5m])))`

