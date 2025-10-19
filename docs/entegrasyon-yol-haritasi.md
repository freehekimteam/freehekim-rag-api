# FreeHekim RAG API – Strateji ve Entegrasyon Yol Haritası

Bu doküman, teknik terimleri aşırı kullanmadan, vizyoner sağlık girişiminizde RAG (Retrieval-Augmented Generation) altyapısının size ne kattığını ve serbest çalışana (freelancer) nasıl teslim edilmesi gerektiğini adım adım özetler.

## 1) Ne Sağlar?
- Daha güvenilir yanıtlar: Sadece model ezberi değil; gerçek kaynaklardan doğrulanmış içerikle cevap.
- Kaynak gösterme: Cevapta [Kaynak 1], [Kaynak 2] olarak referanslar yer alır.
- Tıbbi sorumluluk reddi: Her cevaba otomatik ve tutarlı şekilde eklenir.
- Kişisel veri tutmama: KVKK/GDPR’e uygun; kullanıcı verisi kayıt altına alınmaz.
- Üretime hazır: Sağlık, hazır olma, metrikler, oran limiti gibi korumalar.

## 2) Nasıl Çalışır? (Basit Akış)
- Kullanıcı sorar → Soru metni vektöre dönüştürülür (embedding).
- Vektör DB (Qdrant) içinde iki kaynağa bakılır: Dahili (FreeHekim yazıları) ve harici (genel tıbbi bilgi).
- İki listeden gelen sonuçlar akıllıca birleştirilir (RRF).
- GPT-4 gibi bir modelle cevap üretilir, kaynak ve uyarı eklenir.

## 3) Saha Araştırması – Qdrant Performansı
Amaç: Yanıt kalitesi ve hızını dengede tutmak. İzlemeniz gerekenler:
- Gecikme: Arama süresi (ms). Çok yükselirse `ef_search` düşürülebilir veya kaynak sayısı (topK) optimize edilir.
- Yük: Dakikadaki istek sayısı; CPU ve bellek kullanımı.
- Vektör boyutu ve veri adedi: `1536` boyut; kaç içerik yüklü? (points/vectors sayısı)
- Disk/segment sağlığı: Segment sayısı, optimizasyon ve sıkıştırma.

Nasıl bakarım?
- Qdrant metrikleri: `curl http://localhost:6333/metrics` (Prometheus format)
- Koleksiyon bilgisi (örnek): `client.get_collection(<isim>)` → points_count, vectors_count, status
- Prometheus panelleri: `/metrics` endpoint’inden API metrikleri ve ek RAG metrikleri toplanır.

Basit hedefler (ilk faz):
- Ortalama yanıt süresi: 1–2 saniye (kaynaksız anlaşılması güç sorularda 3–4 sn kabul edilebilir)
- Hata oranı (5xx): < %1
- Kaynak sayısı: 1–3 arası (kısa ve net kalması için)

## 4) Yol Haritası (10 Günlük Plan)
- Gün 0–1: Kurulum kontrolü, `.env` doldurma, sağlık uçları test.
- Gün 2–3: Dahili içeriklerin Qdrant’a yüklenmesi (parçalara bölme, 1536 dim, mükerrerleri temizleme).
- Gün 4–5: Harici kaynakların eklenmesi ve hız/kalite dengesi (topK, `ef_search` ayarı); kısa yük testi.
- Gün 6–7: WordPress/Website entegrasyonu (basit POST → cevap akışı, zaman aşımları, hata yönetimi).
- Gün 8–9: İzleme panelleri (Prometheus/Grafana), uyarılar; oran limiti ve gövde limiti ayarı.
- Gün 10: Kabul testleri, dokümantasyon, canlıya hazırlık.

## 5) Freelancer’a Teslim Paketi
- Depo ve branch: `https://github.com/freehekimteam/freehekim-rag-api.git`, `dev` dalı.
- Çalıştırma:
  - API: `cd fastapi && uvicorn app:app --reload --port 8080`
  - Sağlık kontrol: `GET /health`, `GET /ready`
- Ortam değişkenleri: `.env.example` içinde örnekleri var (OpenAI/Qdrant anahtarları vb.).
- Uç noktalar:
  - `POST /rag/query` body: `{ "q": "Diyabet belirtileri nelerdir?" }`
  - Başarılı cevap: `answer`, `sources[]`, `metadata{}` alanları
  - Hatalar: `400 {"error": "Invalid request"}`, `429`, `413`, `500`
  - Güvenlik (opsiyonel): `REQUIRE_API_KEY=true` ise `X-Api-Key: <key>` header’ı ile çağırın.
- Log ve izleme:
  - İstek başına `X-Request-ID` header’ı
  - `/metrics` ile Prometheus metrikleri + özel RAG metrikleri
- Ops CLI (bakım aracı): `python3 tools/ops_cli.py` — Genel durum, sağlık, Qdrant koleksiyonları, hızlı RAG testi ve cache temizleme için pratik menü.
- Beklentiler (Acceptance):
  - Yanıt süresi ortalaması ≤ 2 sn (staging verisiyle)
  - Cevapta kaynak ve tıbbi uyarı var
  - Hata yönetimi kullanıcı dostu

## 6) Başarı Kriterleri (Kabul Kriterleri)
- Fonksiyonel: Sorulara anlamlı, kaynaklı ve Türkçe anlaşılır cevaplar.
- Güvenlik: KVKK’ye uygun; kişisel veri tutulmuyor; API anahtarları çevrede.
- Dayanıklılık: Oran limiti aktif; gövde limiti aktif; üretime hazır.
- Gözlemlenebilirlik: `/metrics` akıyor; temel paneller hazır; hata oranı izlenebilir.

## 7) Operasyon ve Güvenlik
- Sırlar: `.env` üzerinden, depoda yok; düzenli rotasyon önerilir.
- Ağ: Sunucuda `127.0.0.1`’e bağlanma; dış dünyaya Cloudflare tüneli üzerinden yayınlama.
- Hatalar: Sızıntıyı önlemek için standart `{"error": ...}` cevapları.
- Oran limiti: Kötüye kullanım ve ani yükleri sınırlar (varsayılan: 60/dk/IP).

## 8) Maliyet ve Kapasite
- Embedding maliyeti düşük (tek seferlik indeksleme ağırlıklı).
- Esas maliyet cevap üretimi (LLM). Kısa, kaynaklı cevaplar maliyeti yönetilebilir tutar.
- Ölçek: İlk aşamada tek örnek yeterli; yük arttıkça API örneğini çoğaltma mümkün.

## 9) Sık Sorular
- Q) Cevaplar neden her zaman aynı değil?
  - A) Model ve arama sırası ufak değişiklikler yapabilir; kaynak temelli kalarak stabil hale getirildi.
- Q) İnternet kesilirse ne olur?
  - A) Qdrant çalışıyorsa arama kısmı devam eder; LLM için internet gerekir. Hata mesajı kullanıcı dostudur.
- Q) Ne kadar veri koyabiliriz?
  - A) Binlerce içerik rahatlıkla; büyüdükçe `ef_search`, `topK` ve sıkıştırma/segment ayarlarıyla hız korunur.

## 10) Hızlı Test
- Sağlık: `curl http://localhost:8080/health`
- Hazır olma: `curl http://localhost:8080/ready`
- Soru: `curl -X POST http://localhost:8080/rag/query -H 'Content-Type: application/json' -d '{"q":"Metformin yan etkileri?"}'`
- Metrikler: `curl http://localhost:8080/metrics`

Bu yol haritasıyla; birkaç gün içinde sahada test edilebilir, birkaç hafta içinde ise sürdürülebilir ve izlenebilir bir AI arama/cevap sistemi elde edersiniz.
