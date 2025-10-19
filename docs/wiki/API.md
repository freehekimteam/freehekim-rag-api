# API Referansı

## Uç Noktalar
- `GET /health` – Servis sağlık kontrolü (200)
- `GET /ready` – Hazır olma (Qdrant bağlantısı) (200/503)
- `GET /metrics` – Prometheus metrikleri (text/plain)
- `POST /rag/query` – Soru sor ve yanıt al

## POST /rag/query
İstek gövdesi:
```json
{
  "q": "Diyabet belirtileri nelerdir?"
}
```

Yanıt gövdesi (örnek):
```json
{
  "question": "...",
  "answer": "...",
  "sources": [
    {"text": "...", "source": "internal", "score": 0.0234}
  ],
  "metadata": {
    "internal_hits": 5,
    "external_hits": 3,
    "tokens_used": 450,
    "model": "gpt-4"
  }
}
```

Hata biçimleri:
- `400` – `{ "error": "Invalid request", "details": [...] }`
- `429` – `{ "error": "Rate limit exceeded" }`
- `413` – `{ "error": "Request body too large" }`
- `500` – `{ "error": "Internal server error. Please try again later." }`

Opsiyonel Güvenlik:
- `REQUIRE_API_KEY=true` ise isteklerde `X-Api-Key: <key>` header’ı gönderilmelidir.

## Örnek cURL
```bash
curl -X POST http://localhost:8080/rag/query \
  -H 'Content-Type: application/json' \
  -H 'X-Api-Key: $API_KEY' \
  -d '{"q":"Metformin yan etkileri nelerdir?"}'
```

