# Metrikler

## RAG Özel Metrikleri
- `rag_total_seconds` (Histogram): Pipeline toplam süresi
- `rag_embed_seconds` (Histogram): Embedding süresi
- `rag_search_seconds{collection}` (Histogram): Arama süresi (internal/external)
- `rag_generate_seconds` (Histogram): LLM üretim süresi
- `rag_errors_total{type}` (Counter): Hata sayacı (embedding/database/rag/unexpected)

## HTTP Metrikleri (Instrumentator)
- `http_requests_total`
- `http_request_duration_seconds{le}`

## Örnek PromQL
- `rate(http_requests_total[1m])`
- `histogram_quantile(0.95, sum by (le) (rate(rag_total_seconds_bucket[5m])))`

