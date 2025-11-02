# Yapılandırma (Environment)

Tüm ayarlar `.env` ile yönetilir. Örnekler için `.env.example` dosyasını inceleyin.

Sunucuda sade ve güvenli kurulum için env dosyası kullanıcı dizininde tutulur ve docker-compose bu yolu doğrudan okur:

```bash
# Sunucu (prod)
ENV_FILE=/home/freehekim/.config/freehekim-rag/.env

# Compose dosyası fallback olarak bu yolu kullanır:
# env_file: ${ENV_FILE:-/home/freehekim/.config/freehekim-rag/.env}
```

Yerel geliştirme için repo kökünde `.env` kullanmaya devam edebilirsiniz (ENV_FILE tanımlanmadıysa dev’deki yol devreye girer).

## Temel Değişkenler
- `ENV`: `staging` | `production` | `development` (varsayılan: staging)
- `API_HOST`, `API_PORT`: API servis bind adresi (varsayılan: 127.0.0.1:8080)
- `LOG_LEVEL`: `DEBUG`/`INFO`/… (varsayılan: INFO)

## Qdrant
- `QDRANT_HOST`, `QDRANT_PORT`
- `QDRANT_API_KEY`
- `QDRANT_TIMEOUT` (saniye)

## OpenAI / Embedding
- `EMBED_PROVIDER` = `openai` (varsayılan) | `bge-m3` (gelecek faz)
- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL` = `text-embedding-3-small`

## LLM Üretim
- `LLM_MODEL` (örn. gpt-4, gpt-4o, gpt-4o-mini)
- `LLM_TEMPERATURE` (0–2)
- `LLM_MAX_TOKENS`

## RAG Tuning
- `SEARCH_TOPK`
- `PIPELINE_MAX_CONTEXT_CHUNKS`
- `PIPELINE_MAX_SOURCE_DISPLAY`
- `PIPELINE_MAX_SOURCE_TEXT_LENGTH`

## Korumalar
- `RATE_LIMIT_PER_MINUTE`
- `MAX_BODY_SIZE_BYTES`
- `REQUIRE_API_KEY` (true/false) — üretimde önerilir
- `API_KEY` (X-Api-Key header değeri) — üretimde zorunlu tutulabilir

## Önbellek
- `ENABLE_CACHE` (true/false)
- `CACHE_TTL_SECONDS`

## Örnek .env Parçası
```env
ENV=staging
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_TIMEOUT=10.0
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=800
SEARCH_TOPK=5
PIPELINE_MAX_CONTEXT_CHUNKS=5
PIPELINE_MAX_SOURCE_DISPLAY=3
PIPELINE_MAX_SOURCE_TEXT_LENGTH=200
RATE_LIMIT_PER_MINUTE=60
MAX_BODY_SIZE_BYTES=1048576
ENABLE_CACHE=true
CACHE_TTL_SECONDS=300
REQUIRE_API_KEY=false
# API_KEY=your_api_key_here
```
