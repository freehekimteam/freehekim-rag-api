# Repo Gözden Geçirme – Olası İyileştirme Alanları

Bu liste, üretim olgunluğu açısından atlanmış olabilecek noktaları özetler.

- Lifespan Events: `@app.on_event` deprecate uyarısı var; FastAPI lifespan modeline taşınabilir.
- Uvicorn/Gunicorn Workers: Docker imajında worker sayısı (CPU çekirdeğine göre) parametreleştirilebilir.
- JSON Loglama: Structured JSON log (opsiyonel) ile merkezi log sistemleri için kolay tüketim.
- RAG Token Metrikleri: `rag_tokens_total` (Counter) gibi ek metrikler faydalı olur.
- Qdrant Arama Parametreleri: `ef_search`, `exact`/`hnsw` ayarları ve koleksiyon konfigürasyonu dokümante edilebilir.
- Sağlam Retry Politikaları: OpenAI ve Qdrant için jitter/backoff ayarları .env üzerinden ince ayar yapılabilir.
- Circuit Breaker: Sürekli hata durumunda kısa süreli devre kesme eklenebilir.
- CORS (Gerekirse): Sadece server-to-server kullanılıyorsa gerekmez; tarayıcı doğrudan çağıracaksa eklenir.
- Rate Limit Exceptions: Whitelist/IP bazlı esnetme (örn. WordPress IP’si) opsiyonu.
- Güvenlik Başlıkları: Proxy/Nginx üzerinden ek güvenlik başlıkları (Strict-Transport-Security vb.)
- Testler: RRF birleştirme fonksiyonuna doğrudan unit test; exception handler testleri.
- Build: Docker multi-stage imaj boyutu ve `--platform` varyantları.
- Gözlemlenebilirlik: Trace/Span (OpenTelemetry) entegrasyonu orta vadede.
- Depolama: Qdrant yedekleme/restore runbook’una cron/scheduler örneği.
- İçerik İçe Aktarma: Harici kaynaklar (PubMed vb.) için ingestion pipeline planı.

