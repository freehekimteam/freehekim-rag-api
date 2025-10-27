# Qdrant Rehberi

## Koleksiyonlar
- İçerik boyutu: 1536 (text-embedding-3-small)
- İç: `freehekim_internal`, Dış: `freehekim_external`
 - Sürüm: Qdrant 1.15.5 (docker tag: v1.15.5)

## Sıfırla / Şema (Reset)

Test verilerini temizlemek ve doğru vektör boyutunu (modelden türetilir) zorlamak için araç:

```bash
cd ~/freehekim-rag-api
python3 tools/qdrant_reset.py --yes
# veya özel boyut/mesafe:
# python3 tools/qdrant_reset.py --collections freehekim_internal,freehekim_external --dimension 1536 --distance cosine -y
```

Notlar:
- Araç koleksiyonları SİLER ve yeniden oluşturur.
- Boyut `.env` içindeki embedding modelinden (örn. text-embedding-3-small → 1536) otomatik belirlenir.

## Performans
- Arama kalitesi/hızı topK ve Qdrant parametreleri ile ayarlanır
- `ef_search` ve segment optimizasyonu izlenmelidir

## Metrikler
- Qdrant `/metrics` (Prometheus)
- API tarafında `rag_search_seconds{collection}`

## Yedekleme
- Volume: `/srv/qdrant` → periyodik yedek alın

## Güvenli Erişim (Cloudflare Access ile)

- Yerel erişim (önerilen): SSH tüneli ile `127.0.0.1:6333`.
- Dış erişim gerekiyorsa: `qdrant.hakancloud.com -> http://localhost:6333` (Cloudflare Tunnel)
  - Cloudflare Access zorunlu: yalnızca kurum e‑postaları erişir.
  - WAF genelde gerekmez; Qdrant dashboard/API bazı POST çağrılarına ihtiyaç duyar.
- Ek koruma: Qdrant server API anahtarını zorunlu kılın.
  - Env dosyanıza `QDRANT__SERVICE__API_KEY=<değer>` ekleyin.
  - İstemciler `api-key: <değer>` başlığı ile erişir.

### Doğrulama
```bash
# Sunucuda (lokal)
curl -I http://127.0.0.1:6333/readyz            # 200
curl -I http://127.0.0.1:6333/collections       # 401 (anahtar yoksa)

# Anahtarla
curl -H "api-key: $QDRANT__SERVICE__API_KEY" -I http://127.0.0.1:6333/collections   # 200

# Edge (Access ile)
curl -I https://qdrant.hakancloud.com/          # 302 (Access login)
```
