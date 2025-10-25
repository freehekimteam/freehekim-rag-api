# CI/CD

## Özet
- Bu repo, yerel self‑hosted runner üzerinde çalışan 3 workflow ile gelir:
  - `CI` (dev): Lint/Test
  - `Deploy (manual)`: Bir tıkla docker compose pull/up
  - `Release (on tag)`: `v*.*.*` etiketi push edilince compose pull/up

## Self‑hosted Runner Kurulumu (Bu Cihaz)
1) GitHub → repo → Settings → Actions → Runners → New self‑hosted runner (Linux)
2) Ekrandaki komutları bu cihazda çalıştırın (özet):
   - `mkdir -p /tmp/gha-runner && cd /tmp/gha-runner`
   - Runner paketini indirip açın, `./config.sh --unattended --url <repo> --token <reg_token> --labels linux,deploy`
   - `nohup ./run.sh > /tmp/actions-runner.log 2>&1 &` (kalıcı servis isterseniz `/opt` + `sudo ./svc.sh install && sudo ./svc.sh start`)
3) GitHub → Actions ekranında runner “online” görünmelidir.

Not: Biz hızlı devreye almak için `/tmp/gha-runner` yolunu kullandık (yeniden başlatmada durur). Kalıcı servis kurulumunda `/opt/actions-runner` önerilir.

## Workflow’lar
- `.github/workflows/ci.yml`: Dev’te lint/test (OpenAI anahtarı olmadan smoke seviyesinde)
- `.github/workflows/deploy.yml`:
  - Checkout (fetch‑depth:0)
  - Docker Info (teşhis)
  - Yerel `docker-api:latest` imajı varsa `ghcr.io/freehekimteam/freehekim-rag-api:dev` olarak etiketler (pull gerektirmeden çalışır)
  - `docker compose -f deployment/docker/docker-compose.server.yml pull || true`
  - `docker compose -f ... up -d`
- `.github/workflows/release.yml`: Tag push’ta `pull || true` + `up -d`

## Kullanım
- Manuel deploy: Actions → `Deploy (manual)` → `Run workflow`
- Tag ile release: `git tag -a v2.2.1 -m "Release v2.2.1" && git push origin v2.2.1`

## Notlar
- GHCR özel imaj kullanımı opsiyoneldir; workflow yerelde `docker-api:latest` imajını otomatik etiketleyerek çalıştırır.
- `QDRANT_API_KEY` set edilmemişse compose uyarı logu verebilir; `.env` içinde yönetilir.
## Ana Dal Akışı (Main-First)
- Çalışma dalı: `feat/<slug>` veya `fix/<slug>`
- Hedef dal: `main` (PR üzerinden)
- Zorunluluklar (PR Template):
  - CI (lint/test) geçer
  - Güvenlik taramaları (CodeQL + Trivy) geçer
  - Gizli anahtar yok (diff kontrol)
  - Gerekirse dokümantasyon güncellendi
- Sürümleme:
  - Patch sürümler: küçük düzeltmeler/dokümantasyon/ops (örn. `v2.2.3`)
  - Tag: `v*.*.*` → Release workflow tetikler
- Dağıtım (self‑hosted runner):
  - `Deploy (manual)` veya tag ile `Release` iş akışı
  - Docker compose pull/up ile güncelleme

## Komutlar (Geliştirici İçin Hızlı Akış)
```bash
make dev-install && make lint && make typecheck && make test
make docker-build && make docker-up && make smoketest
```

## Notlar
- `.gitignore` sanal ortamlar ve `AGENTS.md` dahil olacak şekilde güncel
- Pre-commit: `make hooks` ile aktif edin (ruff + küçük temizlikler)
