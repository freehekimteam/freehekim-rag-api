# Sorun Giderme (Troubleshooting)

## 503 /ready
- Qdrant’a erişim yoksa hazır olma 503 döner.
- Kontrol: `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`

## 401 /rag/query
- `REQUIRE_API_KEY=true` ise `X-Api-Key` eksik/yanlış olabilir.

## 429
- Oran limiti aşıldı. `RATE_LIMIT_PER_MINUTE` artırılabilir.

## 413
- Gövde çok büyük. `MAX_BODY_SIZE_BYTES` artırılabilir.

## 500
- Beklenmeyen hata. `/metrics` ve loglar incelenmeli; OpenAI/Qdrant timeout’ları gözden geçirin.

## Prometheus veri çekmiyor
- `/metrics` erişimi, Prometheus hedefleri, Docker network kontrolü.

## Grafana giriş/izin
- Varsayılan kullanıcı/parola ve dizin izinleri.

