# FreeHekim RAG – Mimari Özeti

## Genel Bakış
- İstemci (WordPress/Frontend) → FastAPI → Qdrant + OpenAI
- RAG: Soru → Embedding → İç/Dış arama → RRF birleştirme → LLM ile cevap

## Modüller
- `fastapi/app.py`: Uç noktalar, hata yönetimi, metrikler, korumalar
- `fastapi/config.py`: Ayarlar (.env), doğrulama ve yardımcılar
- `fastapi/rag/embeddings.py`: Embedding üretimi (OpenAI, ileride bge-m3)
- `fastapi/rag/client_qdrant.py`: Qdrant istemcisi ve arama
- `fastapi/rag/pipeline.py`: RAG akışı (RRF, LLM, metrikler)

## Gözlemlenebilirlik
- Prometheus metrikleri: `/metrics`
- RAG metrikleri: toplam/embedding/search/generation histogramları, hata sayaçları

## Güvenlik
- KVKK/GDPR uyumu; kişisel veri tutulmaz
- Oran limiti, gövde boyutu limiti, tek tip hata cevabı

## Yapılandırma
- `.env.example` tüm ayarları listeler; çoğu değer üretimde güncellenebilir.

