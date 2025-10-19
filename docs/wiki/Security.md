# Güvenlik

## Veri Gizliliği
- KVKK/GDPR: Kişisel veri saklanmaz; embedding’e PII dahil edilmez.

## Ağ Mimarisı
- Sunucuda servisler 127.0.0.1’e bind edilir; dış dünyaya Cloudflare Tunnel ile çıkılır.

## Sırlar
- `.env` ile yönetilir; saklama süreleri ve rotasyon politikası uygulanır.

## Çalışma Zamanı Korumaları
- Oran limiti: `RATE_LIMIT_PER_MINUTE`
- Gövde limiti: `MAX_BODY_SIZE_BYTES`
- Tek tip hata cevabı: İç detay sızdırmayı engeller
- İstek kimliği: `X-Request-ID` header’ı
- Opsiyonel API Key: `REQUIRE_API_KEY`/`API_KEY` ve `X-Api-Key` başlığı

