# Dağıtım (Deployment)

## Docker Compose (Production)
```bash
# Ortam değişkenleri
cp .env.example ~/.hakancloud/.env

# Dağıtım
docker compose -f deployment/docker/docker-compose.server.yml up -d
```

- API: 127.0.0.1:8080
- Qdrant: 127.0.0.1:6333 (veri: /srv/qdrant)
  - Sürüm: 1.15.5 (docker image: qdrant/qdrant:v1.15.5)
- Healthcheck’ler compose içinde tanımlıdır.

## Güncelleme
```bash
docker compose -f deployment/docker/docker-compose.server.yml pull
docker compose -f deployment/docker/docker-compose.server.yml up -d
```

## Blue-Green (Özet)
- Yeni stack için farklı proje adıyla compose up
- Sağlık testi → Trafik yönlendirme → Eskiyi kapat
