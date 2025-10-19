# AI Engine Pro Entegrasyonu

## Özet
- AI Engine Pro (WordPress) → Custom Endpoint olarak `POST /rag/query` kullanın.

## Ayarlar
- Method: POST
- URL: `https://<alan-adı>/rag/query`
- Headers:
  - `Content-Type: application/json`
  - (opsiyonel) `X-Api-Key: <key>`
- Body (raw JSON): `{"q":"{{query}}"}`
- Timeout: 30–60 sn

## Hata Yönetimi
- `error` alanı her zaman mevcuttur; 400/429/413/500 durumlarını kullanıcıya uygun mesajla gösterin.

