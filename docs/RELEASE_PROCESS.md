# Sürüm Süreci (Main Yayını Öncesi)

## Branch Stratejisi
- Günlük geliştirme: `dev`
- Yayın: `main`

## Adımlar
1) PR: `dev` → `main`
2) CI: Lint + Test (ci.yml) geçmeli
3) Güvenlik taraması: Trivy (trivy.yml)
4) Versiyon ve CHANGELOG: güncel olmalı
5) Tag: `vX.Y.Z`
6) Dağıtım: Compose ile pull/up veya Actions üzerinden script

## Sürüm Numarası
- `MAJOR.MINOR.PATCH` (örn. `2.1.0`)
- Gerçek kırıcı değişiklikler için `MAJOR` arttırın

## Kabul Kriterleri (Go/No-Go)
- `/health`, `/ready`, `/metrics` çalışıyor
- Örnek `POST /rag/query` başarılı, kaynak ve sorumluluk reddi var
- Grafana panelleri veri alıyor
- Hata oranı makul (5xx <%1)

