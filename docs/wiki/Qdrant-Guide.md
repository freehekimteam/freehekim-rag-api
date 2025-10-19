# Qdrant Rehberi

## Koleksiyonlar
- İçerik boyutu: 1536 (text-embedding-3-small)
- İç: `freehekim_internal`, Dış: `freehekim_external`

## Performans
- Arama kalitesi/hızı topK ve Qdrant parametreleri ile ayarlanır
- `ef_search` ve segment optimizasyonu izlenmelidir

## Metrikler
- Qdrant `/metrics` (Prometheus)
- API tarafında `rag_search_seconds{collection}`

## Yedekleme
- Volume: `/var/lib/qdrant_data` → periyodik yedek alın

