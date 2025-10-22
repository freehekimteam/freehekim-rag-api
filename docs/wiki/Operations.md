# Operasyon (Runbook)

## Başlatma
```bash
docker compose -f deployment/docker/docker-compose.server.yml up -d
```

## Sağlık Kontrolleri
- `GET /health` → 200
- `GET /ready` → 200/503 (Qdrant erişimine göre)

## Metrikler
- `GET /metrics` (Prometheus formatı)
- Grafana panellerini içe aktarın (Monitoring.md)

## Loglama
- Her isteğe `X-Request-ID` eklenir, süreler ms cinsinden loglanır

### Docker Log Rotation
Log dosyalarının büyümesini önlemek için otomatik rotasyon yapılandırılmıştır.

**Kurulum:**
```bash
cd ~/freehekim-rag-api/deployment/docker
sudo bash setup-log-rotation.sh
```

**Ayarlar:**
- Max boyut: 10MB
- Max dosya: 3
- Kompresyon: etkin

**Not:** Script Docker daemon'u yeniden başlatır. Yedek alır ve hata durumunda geri yükler.

## Korumalar
- Oran limiti: `RATE_LIMIT_PER_MINUTE`
- Gövde limiti: `MAX_BODY_SIZE_BYTES`
- Opsiyonel API Key: `REQUIRE_API_KEY`/`API_KEY`

## Ops CLI
```bash
python3 tools/ops_cli.py
```
- Menü: Genel Durum, Sağlık, Qdrant Koleksiyonları, Hızlı RAG Testi, Koruma Bilgisi, Cache, Profil Önerileri (.env)
- Öneri dosyaları: `docs/env-suggestions/`

## Qdrant Bakım
- Koleksiyonları sıfırla ve doğru vektör boyutunu uygula:
```bash
cd ~/freehekim-rag-api
python3 tools/qdrant_reset.py --yes
```
Not: Bu işlem koleksiyonları siler ve yeniden oluşturur. Boyut `.env`’deki embedding modelinden otomatik alınır.

## Yedekleme (Kullanıcı Alanında – Cronless)
- Root gerektirmeden Qdrant verisinin günlük yedeği alınır (Docker ile):
  - Script: `deployment/scripts/backup_qdrant_user.sh`
  - Zamanlayıcı: systemd user timer

### Zamanlayıcıyı kontrol et
```bash
systemctl --user list-timers | grep freehekim-qdrant-backup
```

### Manuel çalıştırma
```bash
systemctl --user start freehekim-qdrant-backup.service
```

Yedekler: `~/backups/qdrant/qdrant-YYYYmmdd-HHMM.tgz` (7 gün saklama)

Not: Kullanıcı oturumu kapalıyken de çalışması için (opsiyonel) `loginctl enable-linger freehekim` komutu root ile verilebilir.
