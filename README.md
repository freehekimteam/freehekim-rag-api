# FreeHekim RAG API

**Retrieval-Augmented Generation (RAG) API for FreeHekim**

Modern, production-ready AI backend providing intelligent medical content search and question-answering capabilities using vector embeddings and GPT-4.

[![CI Status](https://github.com/freehekimteam/freehekim-rag-api/actions/workflows/ci.yml/badge.svg)](https://github.com/freehekimteam/freehekim-rag-api/actions/workflows/ci.yml)
[![Security: Trivy](https://github.com/freehekimteam/freehekim-rag-api/actions/workflows/trivy.yml/badge.svg)](https://github.com/freehekimteam/freehekim-rag-api/actions/workflows/trivy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Architecture

```
┌─────────────┐
│  WordPress  │ (freehekim.com)
│ AI Engine   │
└──────┬──────┘
       │ POST /rag/query
       ▼
┌─────────────────┐
│  FastAPI API    │ :8080
│  ├─ Health      │
│  ├─ Ready       │
│  ├─ RAG Query   │
│  └─ Metrics     │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐  ┌──────────┐
│ Qdrant  │  │  OpenAI  │
│ Vector  │  │ Embed +  │
│   DB    │  │  GPT-4   │
└─────────┘  └──────────┘
```

## Features

- **Dual-Source RAG:** Combines internal (FreeHekim articles) and external medical knowledge
- **Reciprocal-Rank Fusion:** Advanced result merging algorithm
- **Medical Compliance:** Automatic disclaimer injection (Turkish)
- **KVKK/GDPR:** Zero personal data retention
- **Production-Ready:** Health checks, metrics, Docker deployment
- **Operational Hardening:** Rate limiting, body size limits, request IDs, retries
- **CI/CD:** Automated testing, security scanning, deployment

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI 0.115+ |
| Vector Database | Qdrant (latest) |
| Embeddings | OpenAI text-embedding-3-small (1536 dim) |
| LLM | GPT-4 |
| Monitoring | Prometheus + Grafana |
| Deployment | Docker Compose + GitHub Actions |
| Infrastructure | Hetzner VPS + Cloudflare Tunnel |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key
- Qdrant instance (cloud or local)

### Local Development

1. **Clone repository:**
   ```bash
   git clone https://github.com/freehekimteam/freehekim-rag-api.git
   cd freehekim-rag-api
   ```

2. **Setup environment (single .env at repo root):**
   ```bash
   cp .env.example .env
   # Eski kurulumdan ~/.hakancloud/.env varsa, kopyalamak için:
   bash tools/migrate_env.sh
   ```

3. **Install dependencies:**
   ```bash
   cd fastapi
   pip install -r requirements.txt
   ```

4. **Run tests:**
   ```bash
   cd ..
   pytest -v tests/
   ```

5. **Start API (local):**
   ```bash
   cd fastapi
   uvicorn app:app --reload --port 8080
   ```

6. **Test endpoints:**
   ```bash
   # Health check
   curl http://localhost:8080/health

   # Readiness check
   curl http://localhost:8080/ready

   # RAG query
   curl -X POST http://localhost:8080/rag/query \
     -H "Content-Type: application/json" \
     -d '{"q": "Diyabet belirtileri nelerdir?"}'
   ```

### Production Deployment

**Automated via GitHub Actions:**

1. **Run `Deploy (manual)` workflow** → Yerel runner’da docker compose pull/up
2. **Create tag `v*.*.*`** → `Release (on tag)` çalışır, yerel runner’da pull/up

Not: GHCR gerekiyorsa imaj push ekleyin; varsayılan kurulumda workflow, yerelde bulunan `docker-api:latest` imajını `ghcr.io/freehekimteam/freehekim-rag-api:dev` olarak etiketleyip çalıştırır (pull başarısız olsa bile up -d yapılır).

**Manual deployment:**
```bash
# On server
cd ~/freehekim-rag-api
docker compose -f docker/docker-compose.server.yml pull
docker compose -f docker/docker-compose.server.yml up -d
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health status |
| `GET` | `/ready` | Readiness probe (checks Qdrant) |
| `POST` | `/rag/query` | Ask a question, get AI answer |
| `GET` | `/metrics` | Prometheus metrics |

Notes:
- Validation errors return `400` with body `{ "error": "Invalid request", "details": [...] }`.
- Rate limiting returns `429` with `{ "error": "Rate limit exceeded" }`.
- Oversized requests return `413` with `{ "error": "Request body too large" }`.
- Optional security: set `REQUIRE_API_KEY=true` and send `X-Api-Key: <value>` header (see `.env.example`).

### Example Request

```bash
curl -X POST https://rag.hakancloud.com/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "q": "Metformin yan etkileri nelerdir?"
  }'
```

**Response:**
```json
{
  "question": "Metformin yan etkileri nelerdir?",
  "answer": "Metformin'in yaygın yan etkileri...\n\n⚠️ Bu bilgi tıbbi tavsiye değildir. Sağlık kararlarınız için mutlaka hekiminize danışın.",
  "sources": [
    {
      "text": "Metformin, tip 2 diyabet tedavisinde...",
      "source": "internal",
      "score": 0.0234
    }
  ],
  "metadata": {
    "internal_hits": 5,
    "external_hits": 3,
    "tokens_used": 450,
    "model": "gpt-4"
  }
}
```

## Configuration

See `.env.example` for all available options:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Environment (staging/production/development) | `staging` |
| `QDRANT_HOST` | Qdrant server hostname | `localhost` |
| `QDRANT_PORT` | Qdrant port (443=HTTPS, 6333=HTTP) | `6333` |
| `QDRANT_API_KEY` | Qdrant API key | - |
| `QDRANT_TIMEOUT` | Qdrant client timeout (seconds) | `10.0` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `EMBED_PROVIDER` | Embedding provider (openai/bge-m3) | `openai` |
| `LLM_MODEL` | LLM for generation (e.g. gpt-4, gpt-4o) | `gpt-4` |
| `LLM_TEMPERATURE` | LLM sampling temperature (0-2) | `0.3` |
| `LLM_MAX_TOKENS` | Max tokens for answer | `800` |
| `SEARCH_TOPK` | Results per collection | `5` |
| `PIPELINE_MAX_CONTEXT_CHUNKS` | Context chunks to LLM | `5` |
| `PIPELINE_MAX_SOURCE_DISPLAY` | Sources in response | `3` |
| `PIPELINE_MAX_SOURCE_TEXT_LENGTH` | Source preview length (chars) | `200` |
| `RATE_LIMIT_PER_MINUTE` | Requests per IP per minute | `60` |
| `MAX_BODY_SIZE_BYTES` | Max request body size | `1048576` |

## Testing

```bash
# Run all tests
pytest -v tests/

# Run specific test file
pytest tests/test_health.py -v

# Run with coverage
pytest --cov=fastapi tests/
```

## RAG Pipeline Details

1. **Embedding Generation:** User question → OpenAI embedding (1536 dim vector)
2. **Dual Search:** Query both collections (internal + external)
3. **Reciprocal-Rank Fusion:** Merge results using RRF algorithm
4. **Context Extraction:** Select top N chunks (configurable)
5. **Answer Generation:** GPT-4 (configurable) generates answer with citations
6. **Disclaimer Injection:** Automatic medical liability disclaimer (Turkish)

## Monitoring

Prometheus metrics available at `/metrics`:
- Request count & latency
- Error rates
- RAG pipeline performance
 - Total tokens used (rag_tokens_total)

Custom RAG metrics exposed:
- `rag_total_seconds` (Histogram): total pipeline duration
- `rag_embed_seconds` (Histogram): embedding latency
- `rag_search_seconds{collection}` (Histogram): search latency per collection
- `rag_generate_seconds` (Histogram): LLM generation latency
- `rag_errors_total{type}` (Counter): error counts by type (embedding/database/rag/unexpected)
 - `rag_tokens_total{model}` (Counter): total OpenAI tokens used

**Grafana dashboards:**
```bash
# Start monitoring stack
docker compose -f docker/docker-compose.server.yml \
              -f docker/docker-compose.monitoring.yml up -d
```

Access Grafana at `http://localhost:3000` (default: `admin/hakancloud2025`)

## Security

- **Network:** All services bind to `127.0.0.1` (localhost only)
- **Secrets:** Managed via GitHub Environments (90-day rotation)
- **KVKK/GDPR:** No personal data stored or embedded
- **Backups:** Encrypted snapshots, 14-day retention
- **Security Scanning:** Trivy + CodeQL on every commit
- **Protections:** Per-IP rate limiting and request body size limits

Report security issues to: `security@hakancloud.com`

## Development

**Using GitHub Codespaces:**
```bash
# Automatically configured via .devcontainer
# Just open in Codespaces and run:
pytest -v tests/
```

**Local development:**
```bash
# Install dev dependencies
pip install ruff pytest

# Lint code
ruff check fastapi

# Format code
ruff format fastapi

### CLI Kullanımı

FreeHekim RAG için zengin bir CLI mevcuttur. Hem yerel (local pipeline) hem de uzaktaki API ile (remote) çalışabilir.

Temel komutlar:
- Interaktif TUI (yerel):
  - `python3 cli.py`
- Interaktif TUI (uzak API):
  - `python3 cli.py --remote-url https://rag.hakancloud.com --api-key <KEY>`
  - Env desteği: `RAG_API_URL` ve `RAG_API_KEY`
- Tek seferlik sorgu:
  - Yerel: `python3 cli.py -q "Diyabet nedir?"`
  - Uzak: `python3 cli.py -q "..." --remote-url https://... --api-key <KEY>`

Kısayollar:
- `Ctrl+R`: Sorguyu gönder
- `Ctrl+H`: Geçmişi göster
- `Ctrl+L`: Ekranı temizle
- `F1`: Yardım
- `Ctrl+S`: Son sonucu Markdown olarak dışa aktar (`docs/cli-exports/`)

### Ops CLI (Bakım/Teşhis Aracı)

Hızlı bakım ve teşhis için basit bir TUI:

```bash
python3 tools/ops_cli.py
```

Kısayollar: `↑/↓` menü, `Enter/Space` çalıştır, `Ctrl+Q` çıkış.
Menü: Genel Durum, Sağlık, Qdrant Koleksiyonları, Hızlı RAG Testi, Koruma Bilgisi, Cache Durumu/Temizle.

## Error Handling Behavior

- Request validation errors (ör. boş `q`) → `400` + `{"error": "Invalid request"}`
- Bilinçli hatalar (`HTTPException`) → `{"error": "..."}` (tek tip)
- Beklenmeyen hatalar → `500` + `{"error": "Internal server error. Please try again later."}`

```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Support

- **Documentation:** [UPGRADE_NOTES.md](UPGRADE_NOTES.md)
- **Security:** [SECURITY.md](SECURITY.md)
- **Issues:** [GitHub Issues](https://github.com/freehekimteam/freehekim-rag-api/issues)

---

**Built with ❤️ for FreeHekim community**

*Empowering health information through AI*
