# Mimari (Architecture)

## Genel Akış
- Soru → Embedding (OpenAI) → Qdrant (iç/dış arama) → RRF birleştirme → LLM ile cevap → Kaynak ve tıbbi uyarı ekleme

## Modüller
- `fastapi/app.py`: Uç noktalar, hata yönetimi, metrikler, korumalar
- `fastapi/config.py`: Ayarlar (.env), doğrulama
- `fastapi/rag/embeddings.py`: Embedding üretimi
- `fastapi/rag/client_qdrant.py`: Qdrant istemcisi ve arama
- `fastapi/rag/pipeline.py`: RAG akışı (RRF, LLM, metrikler, cache)
- `tools/ops_cli.py`: Bakım ve teşhis TUI

## RAG Aşamaları
1) Embed: Soru metni → 1536 boyutlu vektör (text-embedding-3-small)
2) Arama: İç ve dış koleksiyonlarda benzerlik araması (paralel)
3) RRF: İki listenin sıralamalarını birleştirir
4) Bağlam seçimi: En iyi N parça
5) LLM: GPT-4 serisi ile yanıt + kaynak ve tıbbi uyarı

## Bağımlılıklar
- FastAPI, Uvicorn
- Qdrant (Vector DB)
- OpenAI (Embedding ve LLM)
- Prometheus (metrik), Grafana (görselleştirme)

