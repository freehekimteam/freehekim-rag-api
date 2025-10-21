# Sürüm Süreci

## Branch Stratejisi
- Geliştirme: `dev`
- Yayın: `main`

## Adımlar
1) PR: `dev` → `main`
2) CI: Lint + Test (ci.yml) geçmeli
3) Güvenlik taraması (trivy)
4) CHANGELOG ve sürüm numarası güncel
5) Tag: `vX.Y.Z`
6) Dağıtım: Compose ile pull/up

