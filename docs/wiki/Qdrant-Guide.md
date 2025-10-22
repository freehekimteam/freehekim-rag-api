# Qdrant Rehberi

## Koleksiyonlar
- İçerik boyutu: 1536 (text-embedding-3-small)
- İç: `freehekim_internal`, Dış: `freehekim_external`

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
- Volume: `/var/lib/qdrant_data` → periyodik yedek alın
