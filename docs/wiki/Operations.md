# Operasyon (Runbook)

## Başlatma
```bash
docker compose -f deployment/docker/docker-compose.server.yml up -d
```

## Sağlık Kontrolleri
- `GET /health` → 200
- `GET /ready` → 200/503 (Qdrant erişimine göre)

## Metrikler
- `GET /metrics` (Prometheus formatı)
- Grafana panellerini içe aktarın (Monitoring.md)

## Loglama
- Her isteğe `X-Request-ID` eklenir, süreler ms cinsinden loglanır

## Korumalar
- Oran limiti: `RATE_LIMIT_PER_MINUTE`
- Gövde limiti: `MAX_BODY_SIZE_BYTES`
- Opsiyonel API Key: `REQUIRE_API_KEY`/`API_KEY`

## Ops CLI
```bash
python3 tools/ops_cli.py
```
- Menü: Genel Durum, Sağlık, Qdrant Koleksiyonları, Hızlı RAG Testi, Koruma Bilgisi, Cache, Profil Önerileri (.env)
- Öneri dosyaları: `docs/env-suggestions/`

