# Maliyet Optimizasyonu

## Hızlı Kazanımlar
- `LLM_MODEL`: daha ekonomik model (örn. `gpt-4o-mini`)
- `LLM_MAX_TOKENS`: 600→400
- `SEARCH_TOPK` ve `PIPELINE_MAX_CONTEXT_CHUNKS`: 5→3
- Önbellek: `ENABLE_CACHE=true`, `CACHE_TTL_SECONDS` artırılabilir

## Orta Vadeli
- Batch embedding: API limitlerine göre boyut ayarı
- Metin kırpma: `PIPELINE_MAX_SOURCE_TEXT_LENGTH` düşürün
- Deduplikasyon: benzer chunk’ları tekilleştirin

## Uzun Vadeli
- Yerel embedding (`bge-m3`), kalıcı cache (Redis), dinamik parametre seçimi

## İzleme
- `rag_generate_seconds` ve `rag_total_seconds` düşerken kalite korunuyor mu?

