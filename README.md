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

2. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
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

1. **Push to `dev` branch** → Builds & deploys to staging
2. **Create tag `v*.*.*`** → Builds & deploys to production

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
| `ENV` | Environment (staging/production) | `staging` |
| `QDRANT_HOST` | Qdrant server hostname | `localhost` |
| `QDRANT_PORT` | Qdrant port (443=HTTPS, 6333=HTTP) | `6333` |
| `QDRANT_API_KEY` | Qdrant API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `EMBED_PROVIDER` | Embedding provider (openai/bge-m3) | `openai` |

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
4. **Context Extraction:** Select top 5 chunks
5. **Answer Generation:** GPT-4 generates answer with source citations
6. **Disclaimer Injection:** Automatic medical liability disclaimer (Turkish)

## Monitoring

Prometheus metrics available at `/metrics`:
- Request count & latency
- Error rates
- RAG pipeline performance

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
