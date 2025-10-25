## [2.2.3] - 2025-10-25 - Ops & Güvenlik Düzeltmeleri (Patch)

### Added
- docs: Kurumsal üst seviye `docs/README.md`; `docs/OPERATIONS.md` ve `docs/wiki/Monitoring.md` güncellendi
- ops: `tools/qdrant_verify.py` (koleksiyon/dim uyumluluğu için doğrulama aracı)
- make: `smoketest`, `qdrant-verify`, `hooks` hedefleri

### Changed
- güvenlik: Cloudflare Access + WAF dokümantasyonu; metrics alt alanı yalnızca `/metrics`
- build: `.gitignore` sanal ortamlar (`.venv*`, `.deps`) ve `AGENTS.md` için güncellendi
