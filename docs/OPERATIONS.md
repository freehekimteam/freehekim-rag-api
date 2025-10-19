# Operasyon Rehberi (Runbook)

## Başlatma
```bash
make dev-install
make run
```

## Sağlık Kontrolleri
- Liveness: `GET /health`
- Readiness: `GET /ready` (Qdrant bağlantısını da kontrol eder)

## Metrikler
- Prometheus: `GET /metrics`
- Grafana panelleri: `deployment/monitoring/grafana-dashboards/`

## Loglama
- Her isteğe `X-Request-ID` eklenir
- Süreler ms cinsinden loglanır

## Korumalar
- Oran limiti (IP başına/dk): `RATE_LIMIT_PER_MINUTE`
- Gövde limiti (byte): `MAX_BODY_SIZE_BYTES`

## Dağıtım
- Docker Compose dosyaları: `deployment/docker/`
- Hızlı başlat: `make docker-up`

## Geri Alma (Rollback)
- Önceki imaj/etiketle compose’ı yeniden başlatın
- Yedeklerden Qdrant verisini geri yükleyin (gerekirse)

## Olay Yönetimi
- Yüksek hata oranı: Grafana uyarıları → Loglar → `/ready` kontrolü
- Qdrant gecikmesi yüksek: `SEARCH_TOPK` ve `ef_search` (Qdrant) ayarlarını gözden geçirin

