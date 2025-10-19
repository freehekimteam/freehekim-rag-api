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

## Ops CLI (Acil Durum ve Bakım)
```bash
python3 tools/ops_cli.py
```

Kısayollar: `↑/↓` menü seçimi, `Enter/Space` çalıştır, `Ctrl+Q` çıkış.

Menü başlıkları:
- Genel Durum (env, LLM, Qdrant, limitler, cache)
- Sağlık Kontrolleri (Health/Ready eşdeğeri)
- Qdrant Koleksiyonları (isim ve point sayıları)
- Hızlı RAG Testi (tek soru/cevap)
- Koruma Ayarları (bilgilendirme)
- Cache Durumu / Temizle (opsiyonel)
- Profil Önerileri (.env yazdır):
  - Maliyet Odaklı: `gpt-4o-mini`, daha düşük token/bağlam ve daha uzun cache TTL.
  - Performans Odaklı: `gpt-4o`/`gpt-4`, daha yüksek token/topK/bağlam ve kısa cache TTL.
  - Not: Üretilen dosyalar `docs/env-suggestions/` klasörüne yazılır, mevcut `.env` otomatik değişmez.

## Geri Alma (Rollback)
- Önceki imaj/etiketle compose’ı yeniden başlatın
- Yedeklerden Qdrant verisini geri yükleyin (gerekirse)

## Olay Yönetimi
- Yüksek hata oranı: Grafana uyarıları → Loglar → `/ready` kontrolü
- Qdrant gecikmesi yüksek: `SEARCH_TOPK` ve `ef_search` (Qdrant) ayarlarını gözden geçirin
