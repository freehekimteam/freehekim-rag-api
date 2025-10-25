# Dokümantasyon – Güncel Durum

Bu belge, deponun mevcut ve üretime hazır durumunun kısa, kurumsal bir özetidir. Eski/çelişkili içerikler referans amaçlıdır; yetkili kaynaklar aşağıda listelenmiştir.

## Hızlı Başlangıç
- Bağımlılıklar: `make dev-install`
- Lint/format/tip kontrolü: `make lint && make format && make typecheck`
- Testler: `make test`
- Yerelde çalıştır: `make run` (127.0.0.1:8080)

## Üretim (Docker + Compose)
- İmaj: `make docker-build`
- Başlat/Durdur: `make docker-up` / `make docker-down`
- Smoke test: `make smoketest`

Erişim, Cloudflare Tunnel üzerinden sağlanır (inbound port açılmaz). Yapılandırma: `infrastructure/cloudflare/tunnel-config.yml`.

## Cloudflare Tunnel (Özet)
- Oturum: `cloudflared tunnel login`
- Tünel: `cloudflared tunnel create freehekim-rag`
- DNS: `cloudflared tunnel route dns freehekim-rag rag.hakancloud.com`
- Servis: `sudo cloudflared service install && sudo systemctl enable --now cloudflared`
- Doğrulama: `curl https://rag.hakancloud.com/health`

## Qdrant Doğrulaması
- Boyut/koleksiyon kontrolü: `make qdrant-verify`
- Uyuşmazlıkta reset: `python3 tools/qdrant_reset.py --yes`

## Güvenlik ve Konfigürasyon
- `.env` (üretim): `ENV=production`, `REQUIRE_API_KEY=true`, güçlü `API_KEY`.
- Oran/Gövde limitleri varsayılan olarak aktif; gerekmiyorsa değiştirmeyin.
- Prometheus metrikleri `/metrics` (Access ile kısıtlayın) veya `/secure-metrics` (X-Api-Key) üzerinden.

## Yetkili Belgeler
- Mimari: `docs/ARCHITECTURE.md` ve `docs/wiki/Architecture.md`
- Dağıtım: `docs/wiki/Deployment.md`
- Yapılandırma: `docs/wiki/Configuration.md`
- Operasyon: `docs/OPERATIONS.md`, `docs/wiki/Operations.md`
- Güvenlik: `docs/wiki/Security.md`
- API Referansı: `docs/wiki/API.md`

Not: `docs/PR_RELEASE_*` ve `docs/marketing/` klasörleri tarihçedir; güncel kararlar için bu belge ve “Yetkili Belgeler” önceliklidir.
