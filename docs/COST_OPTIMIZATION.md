# Maliyet Optimizasyonu

Bu sayfa, aylık OpenAI/Qdrant maliyetlerini düşürmeye yönelik pratik önerileri listeler.

## Kısa Vadeli (Hızlı Kazanımlar)
- LLM modeli: `LLM_MODEL` için daha ekonomik model (ör. `gpt-4o-mini`) değerlendirin.
- Max tokens: `LLM_MAX_TOKENS` değerini 600→400 gibi düşürün.
- Kaynak sayısı: `SEARCH_TOPK` ve `PIPELINE_MAX_CONTEXT_CHUNKS` değerlerini azaltın (5→3).
- Cevap uzunluğu: Soruda “kısa ve net” gibi yönlendirme ekleyin.
- Önbellek: `ENABLE_CACHE=true` ile aynı soruların tekrarında LLM çağrısını atlayın.

## Orta Vadeli
- Embedding toplu işlemleri: `embed_batch` ile batch boyutlarını optimize edin (API limitleri dahilinde).
- Metin kırpma: Kaynak önü izleme uzunluğunu (`PIPELINE_MAX_SOURCE_TEXT_LENGTH`) düşürün.
- Deduplikasyon: Aynı/similar metin chunk’larını tekilleştirin.

## Uzun Vadeli
- Yerel embedding: `EMBED_PROVIDER=bge-m3` (yerel model) — ilk fazda dokümante, sonraki fazda devreye alınabilir.
- Önbellek/doğru yanıt veri tabanı: Sık sorulanların yanıtını kalıcı cache’de tutma (Redis gibi).
- Dinamik ayar: Trafik/yük durumuna göre `topK`, `tokens`, model seçimi dinamik yapılabilir.

## İzleme
- `rag_generate_seconds` ve `rag_total_seconds` düşerken kalite korunuyor mu?
- Token kullanımı ve cevap kalitesi ticaret-off’u izleyin.
