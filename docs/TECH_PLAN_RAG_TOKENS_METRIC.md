# Teknik Plan – RAG Token Metriği

Amaç: LLM çağrılarında kullanılan token sayısını Prometheus’a Counter olarak raporlamak.

## Hedef Metrik
- Ad: `rag_tokens_total`
- Tip: Counter
- Etiketler: (opsiyonel) `model` (örn. gpt-4, gpt-4o-mini)
- Anlam: Toplam kullanılan OpenAI token sayısı (cevap üretimi sırasında)

## Uygulama Adımları
1. pipeline.py içinde Prometheus bölümüne ekleyin:
   ```python
   from prometheus_client import Counter
   RAG_TOKENS_TOTAL = Counter("rag_tokens_total", "Total OpenAI tokens used", labelnames=("model",))
   ```
2. `generate_answer` içinde, yanıt alındıktan sonra:
   ```python
   tokens_used = getattr(response.usage, "total_tokens", 0)
   if RAG_TOKENS_TOTAL:
       RAG_TOKENS_TOTAL.labels(model=settings.llm_model).inc(tokens_used)
   ```
3. Hata ve fallback durumlarında token artışı yapılmaz (0).
4. Dokümantasyon güncelle:
   - README.md Monitoring bölümüne `rag_tokens_total` ekleyin
   - docs/wiki/Metrics.md ve Monitoring.md sayfalarına ekleyin
5. Dashboard güncelle (opsiyonel):
   - Panel: `rate(rag_tokens_total[5m])` ile dakika başına token tüketimi

## Test Planı
- Unit test: `generate_answer` sahte `response.usage.total_tokens=123` ile metric artışı doğrulanır
- Smoke: `/metrics` çıktısında `rag_tokens_total` ve `_total` artışının görülmesi

## Riskler
- Çok yoğun trafikte Counter artışı CPU-maliyeti minimaldir; düşük risk
- Metrik adı değişikliği avoided; backward compatible isim seçildi

