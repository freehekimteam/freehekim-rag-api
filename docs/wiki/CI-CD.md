# CI/CD

## GitHub Actions
- Workflow dosyaları izin gerektirir (workflow scope). Bu nedenle örnek dosyalar `docs/CI_WORKFLOWS/` altındadır.
- İzin verildiğinde `.github/workflows/` altına taşın.

Önerilen işler:
- `ci.yml`: Lint (ruff), Test (pytest)
- `trivy.yml`: Container güvenlik taraması

## Branch ve Sürüm
- Geliştirme: `dev`
- Yayın: `main`
- Tag: `vX.Y.Z`

