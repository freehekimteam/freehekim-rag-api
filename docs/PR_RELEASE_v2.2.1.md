# Release v2.2.1 — Lifespan, Token Metrikleri, Runtime Tuning (Patch)

Bu sürüm 2.2.0’ın patch güncellemesidir. CI/CD ve self‑hosted runner akışları iyileştirildi; deploy step’inde lokal imaj etiketleme ve registry hatalarına karşı dayanıklılık eklendi. Fonksiyonel değişiklik yok; üretim davranışı korunur.

## Öne Çıkanlar
- Deploy/Release workflow’ları: Lokal `docker-api:latest` imajı yoksa registry pull; varsa otomatik `ghcr.io/...:dev` olarak etiketleyip `up -d`
- Runner sertleştirme: Checkout fetch‑depth:0, clean ve eski `.wiki-publish` kalıntılarının sanite temizliği
- Docs: CI/CD ve Deployment belgeleri self‑hosted açıklamalarıyla güncellendi

## Test Planı
- Actions → Deploy (manual) → Yeşil koşu
- Tag: `v2.2.1` → “Release (on tag)” yeşil koşu
- `docker compose -f deployment/docker/docker-compose.server.yml up -d` sonrası:
  - `GET /health` → 200
  - `GET /ready` → 200/503
  - 1–2 RAG çağrısı → `/metrics` içinde `rag_tokens_total{model}` artışı

## Riskler ve Azaltım
- Sadece CI/CD akışları ve deploy sertleştirmeleri; uygulama davranışı değişmedi
- GHCR erişimi olmasa bile lokal imajla “up -d” devam eder

