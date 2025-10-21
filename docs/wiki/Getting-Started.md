# Getting Started

Bu bölüm, projeyi hızlıca çalıştırmanız için gereken adımları içerir.

## Önkoşullar
- Docker ve Docker Compose
- (Opsiyonel) Python 3.11+ geliştirici ortamı
- Qdrant ve OpenAI için erişim anahtarları

## Hızlı Başlangıç (Docker Compose)
1) Depoyu klonlayın
```bash
git clone https://github.com/freehekimteam/freehekim-rag-api.git
cd freehekim-rag-api
```

2) Ortam değişkenlerini ayarlayın
```bash
cp .env.example ~/.hakancloud/.env
# Değerleri düzenleyin: OPENAI_API_KEY, QDRANT_* vb.
```

3) Çalıştırın
```bash
docker compose -f deployment/docker/docker-compose.server.yml up -d
```

4) Doğrulama
```bash
curl http://localhost:8080/health   # 200
curl http://localhost:8080/ready    # 200/503 (Qdrant’a bağlı)
```

5) RAG Sorgusu (örnek)
```bash
curl -X POST http://localhost:8080/rag/query \
  -H 'Content-Type: application/json' \
  -d '{"q":"Diyabet belirtileri nelerdir?"}'
```

Not: Güvenliği artırmak için X-Api-Key’i aktif edebilirsiniz (Configuration.md → REQUIRE_API_KEY).

## Geliştirici Rejimi (Opsiyonel)
- Makefile kısayolları: `make dev-install`, `make run`, `make test`
- Ops CLI: `python3 tools/ops_cli.py`

Daha fazla bilgi: Configuration.md, Operations.md

