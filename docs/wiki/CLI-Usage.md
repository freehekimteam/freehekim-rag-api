# CLI Kullanımı

FreeHekim RAG CLI, hem yerel (local) pipeline ile hem de uzaktaki API üzerinden çalışabilir.

## Modlar
- Yerel: `python3 cli.py`
- Uzak API: `python3 cli.py --remote-url https://rag.example.com --api-key <KEY>`
  - Env değişkenleri: `RAG_API_URL`, `RAG_API_KEY`

## Tek Seferlik Sorgu
- Yerel: `python3 cli.py -q "Diyabet nedir?"`
- Uzak:  `python3 cli.py -q "..." --remote-url https://... --api-key <KEY>`

## Kısayollar (TUI)
- `Ctrl+R`: Gönder
- `Ctrl+H`: Geçmiş
- `Ctrl+L`: Temizle
- `F1`: Yardım
- `Ctrl+S`: Son sonucu Markdown olarak dışa aktar (`docs/cli-exports/`)

## İpucu
- Başlıkta çalışma modu görünür: `MODE=LOCAL ENV=...` veya `MODE=REMOTE https://...`

