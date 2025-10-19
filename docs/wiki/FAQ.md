# SSS (FAQ)

## Cevaplar neden her zaman aynı değil?
- Model ve arama sırası değişebilir; kaynak temelli yaklaşım stabiliteyi artırır.

## İnternet kesilirse ne olur?
- Qdrant çalışıyorsa arama kısmı devam eder; LLM için internet gerekir.

## Kaç içerik desteklenir?
- Binlerce belgeyi destekler; topK ve Qdrant parametreleriyle ölçeklenir.

## AI Engine Pro ile çalışır mı?
- Evet. `POST /rag/query` ile `{"q":"..."}` body; opsiyonel `X-Api-Key` başlığı.

