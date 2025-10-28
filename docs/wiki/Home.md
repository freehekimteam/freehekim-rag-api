# FreeHekim RAG API – Wiki

Bu wiki, projeyi A’dan Z’ye kapsayan kurumsal seviyede bir başvuru kaynağıdır. Aşağıdaki bölümler üzerinden hızlıca ilerleyebilirsiniz.

- Getting Started: Getting-Started.md
- Mimari: Architecture.md
- Yapılandırma (Environment): Configuration.md
- API Referansı: API.md
- Operasyon (Runbook): Operations.md
- İzleme ve Paneller: Monitoring.md
- Güvenlik: Security.md
- Dağıtım: Deployment.md
- CI/CD: CI-CD.md
- Maliyet Optimizasyonu: Cost-Optimization.md
- Sorun Giderme: Troubleshooting.md
- SSS: FAQ.md
- Katkı Rehberi: Contributing.md
- Sürüm Süreci: Release-Process.md
- AI Engine Pro Entegrasyonu: Integration-AI-Engine-Pro.md
- Ops CLI: Ops-CLI.md
- CLI Kullanımı: CLI-Usage.md
- Qdrant Rehberi: Qdrant-Guide.md
- Metrikler: Metrics.md
- Terimler Sözlüğü: Glossary.md
- Yol Haritası: Roadmap.md

Önemli: Bu wiki’deki başlıklar repository içindeki dokümanlarla (docs/*.md) uyumludur ve gerekli yerlerde güncel örnekleri referans gösterir.

## Server via systemd (Hızlı Özet)

Üretim sunucusunda servisleri systemd ile yönetmek için özet adımlar:

1) Prod env dosyası (tek dosya, sistem dizini)
```bash
sudo mkdir -p /etc/freehekim-rag
sudo cp .env.example /etc/freehekim-rag/.env
sudo chgrp ragsvc /etc/freehekim-rag/.env 2>/dev/null || true
sudo chmod 640 /etc/freehekim-rag/.env
```

2) Provision + servis (önerilen otomasyon)
```bash
sudo bash deployment/scripts/provision_freehekim_rag.sh
sudo systemctl enable --now freehekim-rag.service
```

3) Sağlık ve bileşenler
- API: `http://127.0.0.1:8080/health`, `http://127.0.0.1:8080/ready`
- Qdrant: `127.0.0.1:6333` (API key gerekli)
- Prometheus: `http://127.0.0.1:9090`
- Alertmanager: `http://127.0.0.1:9093`
- Grafana: `http://127.0.0.1:3000`

4) Günlük yedekleme (incremental)
- Timer: `freehekim-rag-backup.timer` (03:30)
- Log: `/var/backups/freehekim-rag/backup.log`
- Son yedek: `/var/backups/freehekim-rag/latest`

5) Hızlı geri yükleme (özet)
```bash
sudo systemctl stop freehekim-rag.service
sudo rsync -a --delete /var/backups/freehekim-rag/latest/qdrant/ /srv/qdrant/
sudo rsync -a --delete /var/backups/freehekim-rag/latest/etc/ /etc/freehekim-rag/
sudo systemctl start freehekim-rag.service
```

Not: Portlar yalnızca `127.0.0.1`’e bağlıdır; dış erişim için Cloudflared tünel kullanılır.

## Compose (Docker) Env Notu

- Compose env kaynağı: `ENV_FILE=/home/freehekim/.config/freehekim-rag/.env`
- İzinler: `chmod 600 ~/.config/freehekim-rag/.env`
