# Release v2.2.0 — Lifespan, Token Metrikleri, Runtime Tuning

## Özet
FastAPI yaşam döngüsü modern “lifespan”e taşındı, RAG token tüketimi ölçümü eklendi, Uvicorn worker sayısı parametrik hale getirildi ve JSON log desteği opsiyonel olarak eklendi. İzleme panelleri ve dokümantasyon güncellendi.

## Öne Çıkanlar
- Lifespan: `@app.on_event` → `lifespan` (deprecation güvenli)
- Metrik: `rag_tokens_total{model}` (Prometheus); Grafana’da “Tokens per minute” paneli
- Runtime: `UVICORN_WORKERS` env ile worker sayısı; `LOG_JSON=true` ile JSON log
- Dokümanlar: README + Wiki (Monitoring/Metrics, Config) güncellendi; ekip özeti eklendi
- Ops CLI: Qdrant HNSW parametrelerini (mümkünse) gösterir

## Değişiklikler
- App lifecycle: `fastapi/app.py` (lifespan)
- Metrikler: `fastapi/rag/pipeline.py` (rag_tokens_total; labels: model)
- Dashboard: `deployment/monitoring/grafana-dashboards/rag-overview.json` (tokens paneli)
- Runtime: `deployment/docker/Dockerfile.api` (workers); `fastapi/requirements.txt` (python-json-logger opsiyonel)
- Config/env: README ve `.env.example` → `LOG_JSON`, `UVICORN_WORKERS`
- Dokümanlar: Wiki/Monitoring+Metrics, `docs/TEAM_BRIEF_TR.md`

## Test Planı
- Smoke (staging):
  - `GET /health` → 200
  - `GET /ready` → 200/503 (Qdrant’a göre)
  - `POST /rag/query` `{}` → 400 ve `{"error": "..."}`
  - 1–2 gerçek RAG çağrısı yap
- İzleme:
  - `/metrics` içinde `rag_tokens_total{model}` artmalı
  - Grafana “Tokens per minute” panelinde hareket gözlenmeli
- Log/Workers:
  - `LOG_JSON=true` ile JSON format (stdout)
  - `UVICORN_WORKERS=2..4` deneyerek CPU’ya göre doğrula

## Dağıtım Planı
- Env: (opsiyonel) `LOG_JSON=false|true`, `UVICORN_WORKERS=2`
- Compose:
  - `docker compose -f deployment/docker/docker-compose.server.yml pull`
  - `docker compose -f deployment/docker/docker-compose.server.yml up -d`

## Geri Alma (Rollback)
- Önceki imaj etiketine dön:
  - `docker compose -f deployment/docker/docker-compose.server.yml down`
  - Önceki tag ile `pull` + `up -d`

## Riskler ve Azaltım
- Lifespan geçişi davranışı değiştirmez
- `rag_tokens_total` ekleme “backward compatible”
- `LOG_JSON` varsayılan “false”; `UVICORN_WORKERS` varsayılan “2”

## Kabul Kriterleri (Go/No-Go)
- `/health` 200, `/ready` 200/503
- `rag_tokens_total{model}` artışı ve panelde hareket
- Ortalama gecikmede artış yok; 5xx oranı düşük
- Rate/body limit ve `X-Api-Key` (opsiyonel) davranışı değişmedi

## İlgili PR’lar
- `feature/rag-tokens-metric`
- `feature/uvicorn-workers-jsonlog`
- `feature/lifespan-lifecycle`

