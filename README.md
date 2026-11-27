# ◆ Atölye Paneli

Kişiye özel üretim yapan küçük atölyeler (kuyumcu, filografi, el sanatı) için
**sipariş → üretim → teslim** takibi, müşteri takip linki, vitrin sayfası ve abonelik. Çok kiracılı (multi-tenant) SaaS.

7 kişilik ileri Python + web sınıfının 6 haftalık ortak ürünüdür (2 Kasım – 27 Kasım 2026, kod kapanışı).
Ödeme yalnızca **test ortamında** çalışır, gerçek para alınmaz ([docs/KARARLAR.md](docs/KARARLAR.md)).

---

## 1. Çalıştırma (yerel, 5 dakika)

Gerekenler: Python 3.12+ (CI 3.13 kullanır), git.

```bash
git clone https://github.com/fatihsahinbas/atolye-paneli.git
cd atolye-paneli
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                       # Windows: copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
#   ↑ çıktıyı .env içindeki SECRET_KEY= satırına yapıştır
alembic upgrade head
python -m scripts.seed_demo                # demo atölye, ürün, müşteri, sipariş
uvicorn --factory app.main:create_app --reload
```

| Adres | Ne var |
|---|---|
| http://localhost:8000 | Giriş → **demo@atolye.local** / **demo-sifre-123** |
| http://localhost:8000/v/demo-atolye | Atölye vitrini (herkese açık) |
| http://localhost:8000/fiyatlar | Paketler (herkese açık) |
| http://localhost:8000/kvkk | KVKK aydınlatma metni |
| http://localhost:8000/docs | API dokümanı (yalnız geliştirme ortamında) |

Varsayılan `.env` ile hiçbir dış servise bağlanmaz: bildirimler log'a yazılır (`NOTIFY_CHANNEL=console`),
e-posta log'a yazılır (`SMTP_HOST` boş), ödeme demo sayfasıyla yapılır (`PAYMENT_PROVIDER=fake`).

### Kontroller (CI'ın yaptığının aynısı)

```bash
ruff check .                               # lint
pytest -q                                  # 161 test
alembic upgrade head && alembic check      # migration'lar modellerle uyumlu mu
pip-audit -r requirements.txt              # bilinen açığı olan paket var mı
```

Modeli değiştirdiysen: `alembic revision --autogenerate -m "ne değişti"` → dosyayı **oku** → commit.

### Demo senaryosu (11 Aralık sunumu için)

1. `demo@atolye.local` ile gir → **Pano**: kartlar sürükle-bırak ile sütun değiştirir; terminine 2 gün kalan sarı, geçen kırmızı.
2. **Yeni sipariş**: "+ Kalem ekle" ile birden çok ürün; toplam ve termin önerisi kendiliğinden gelir.
3. Sipariş detayı → durumu değiştir → **Gönderilen bildirimler** tablosu. Müşteri takip linkini (`/t/...`) yeni sekmede aç.
4. **Ürünler → Düzenle**: 2–3 fotoğraf yükle, birini kapak yap → **Vitrin ↗**'de kapak görünür.
5. **Abonelik** → paket seç → **Öde** → "Test ödemesini tamamla" → bitiş tarihi 1 ay uzar, "Son ödemeler"de `PAID`.
6. Pilot atölye: `python -m scripts.make_pilot demo-atolye` → Abonelik sayfasında "Pilot programı: ücretsiz", ödeme butonu yok
   (geri almak için `--geri-al`).

### Gerçek sağlayıcılarla (isteğe bağlı)

`.env` içinde ilgili satırları doldur; anahtarlar **asla** commit edilmez.

| Ne | Ayar |
|---|---|
| SMS / WhatsApp | `NOTIFY_CHANNEL=sms` veya `whatsapp` + `SMS_API_URL/KEY`, `WHATSAPP_API_URL/KEY` |
| E-posta (bildirim + şifre sıfırlama) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD` |
| iyzico sandbox | `PAYMENT_PROVIDER=iyzico`, `IYZICO_API_KEY`, `IYZICO_SECRET_KEY` (adres sandbox'ta kalır) |
| PayTR test | `PAYMENT_PROVIDER=paytr`, `PAYTR_MERCHANT_ID/KEY/SALT`, `PAYTR_TEST_MODE=1`, `PUBLIC_BASE_URL` |

**Canlı ödeme kilidi:** `PAYMENT_LIVE=false` (varsayılan) iken iyzico sandbox dışı bir adresle ya da PayTR `TEST_MODE=0` ile
uygulama **açılmaz**. PayTR bildirimi internetten erişilen adrese gelir; `localhost`'ta yalnız `fake` ve testler çalışır.

---

## 2. Production (Docker)

```bash
cp .env.example .env      # "Production" bölümünü doldur: ENV=prod, COOKIE_SECURE=true, DATABASE_URL, DOMAIN...
docker compose up -d --build
```

Caddy (HTTPS, otomatik sertifika) → FastAPI → PostgreSQL. Konteyner açılırken `alembic upgrade head` çalışır.
DB portu dışarı açılmaz. Yedek: `scripts/backup.sh` (gpg şifreli). Prod'da `/docs` kapalıdır.

---

## 3. Özellikler (son hâl, 27 Kasım 2026)

| Alan | Ne yapıyor | Sahip | PR |
|---|---|---|---|
| Kayıt / giriş / oturum | Argon2id şifre, HttpOnly çerez, rate limit, hesap silme | Hasan | iskelet |
| Personel | OWNER, STAFF ekler / pasifleştirir; pasifleşince oturumları düşer | Hasan | #7 |
| Şifre sıfırlama | 30 dk, tek kullanımlık, DB'de SHA-256 hash; "hesap var mı" sızdırmaz | Hasan | #12 |
| KVKK | `/kvkk` aydınlatma metni; **bildirim** ve **kampanya** izni ayrı; izin geri alınabilir; müşteri anonimleştirme (bildirim geçmişi dahil) | Hasan | #22 |
| Abonelik ödemesi | Paket seç → öde → bitiş tarihi +1 ay. Fake / iyzico / PayTR adaptörü, idempotent, tutar kontrolü, 14 gün deneme, pilot atölye ücretsiz | Hasan | #25 |
| Marka | Renkler yalnız `:root`'ta (AA kontrast testi), Inter font, logo, ürün adı tek ayar (`APP_NAME`) | Seher | #3 |
| Vitrin | `/v/{slug}`: ürün kartı, modal, kapak görseli, WhatsApp'tan sipariş butonu | Seher | #6, #24 |
| Atölye ayarları | Ad + telefon (`0532…` → `+90532…`), vitrin linki salt okunur | Seher | #17 |
| Fiyat motoru | Sabit / altın (gram × milyem + işçilik) / maliyet + kâr; Decimal, sipariş anında dondurulur | Hayrettin | #8 |
| Ürün düzenleme | Aktif/pasif, vitrinde göster, ortalama üretim süresi; hatalı girişte form korunur | Hayrettin | #19 |
| Paketler | `/fiyatlar`: Başlangıç (ücretsiz, 20 sipariş), Atölye 950 ₺, Usta Pro 1.950 ₺; `PILOT` gizli | Hayrettin | #19 |
| Çok kalemli sipariş | HTMX ile kalem ekle/sil, canlı toplam, pasif ürün eklenemez | Çınar | #20 |
| Sürükle-bırak pano | Karar sunucuda (`change_status`); geçersiz geçişte 409, kart geri döner | Çınar | #20 |
| Termin | İş günü + TR resmî tatilleri 2026–2027; en uzun üretim süresinden öneri; panoda sarı/kırmızı | Çınar | #21 |
| Bildirim | Telefon varsa SMS/WhatsApp, yoksa e-posta, rıza yoksa gönderilmez; geçmiş + "Tekrar gönder" | Deha | #5, #23 |
| Takip linki | `/t/{kod}`: müşteri adımları ve paylaşılan fotoğrafları görür, kişisel veri yok | Deha | iskelet |
| Medya | Magic-byte kontrolü, EXIF/GPS silinir, 400 px küçük resim | Alper | #4 |
| Ürün galerisi | Ürün başına 8 görsel, tek kapak, silince dosyalar da silinir | Alper | #24 |

Kapanış günü (27 Kas) tamamlanan işler: #19, #20, #21, #22, #23, #24, #25, #26 (review düzeltmeleri).
Öğrencinin teslimi olmayan ya da projeye uymayan modüller Fatih tarafından tamamlandı; hangi PR'da ne yapıldığı PR açıklamalarında yazıyor.

### Yapılmayanlar / sonraki adımlar

- **Teklif / proforma PDF** (Hayrettin H3): #13 projeye uymadığı için alınmadı; PR'daki 6 adımlık yol geçerli.
- **Paket sınırının uygulanması**: `can_create_order` hazır, sipariş oluşturmaya bağlanmadı; süresi biten abonelikte yalnız uyarı var, engelleme yok.
- **Takip sayfasında "ürününüz yapılıyor" videosu** (Alper H4) ve **lansman içerik planı** (Deha H4): kod dışı / yapılmadı.
- Güvenlik checklist açıkları: #20 yedek cron + restore testi, #22 harcama alarmı, #23 saldırı testi;
  rate limit tek süreçte (çok worker'da Redis gerekir); sipariş/taşıma uçlarında eşzamanlılık kilidi.
- Pilot atölye kurulumu (3 atölye) ve 1 sayfalık hızlı başlangıç kılavuzu.

---

## 4. Mimari

Modüler monolit. Her modül kendi `models.py / service.py / router.py` dosyalarına sahip.
`app/domain/` saf Python'dur (FastAPI/SQLAlchemy import etmez), tek başına test edilir.

```
app/
  core/        config, db, güvenlik, tenant izolasyonu (scoped/get_owned), şablon, log maskeleme
  domain/      order_status (state machine) · pricing (fiyat motoru) · plans (paketler)
               deadline (termin, tatiller) · subscription (abonelik süresi)
  modules/
    auth/          Hasan     kayıt, giriş, oturum, personel, şifre sıfırlama
    workshop/      Hasan+Seher  atölye (tenant), ayarlar
    customers/     Deha+Hasan   müşteri, KVKK izinleri, anonimleştirme
    legal/         Hasan     /kvkk
    catalog/       Seher+Hayrettin  ürün, düzenleme, fiyat önizleme, /fiyatlar
    orders/        Çınar     sipariş, kalemler, pano, durum geçişi, termin önerisi
    media/         Alper     güvenli görsel yükleme, ürün galerisi
    notifications/ Deha      bildirim outbox, SMS/WhatsApp/e-posta adaptörleri, tekrar gönder
    tracking/      Deha      /t/{kod} müşteri takip sayfası
    showcase/      Seher     /v/{slug} vitrin, /v/{slug}/gorsel/{id}
    payments/      Hasan     abonelik, ödeme sağlayıcıları, dönüş uçları, genel HMAC webhook
  templates/ static/          Seher (UI/marka) · JS: app.js (sipariş formu), board.js (pano), showcase.js
migrations/   Alembic (7 sürüm)
scripts/      seed_demo.py · make_pilot.py · backup.sh
tests/        161 test: domain, auth, IDOR, upload, ödeme, bildirim, KVKK, pano, galeri
```

### Altın kurallar

1. Tenant tablosuna erişim **yalnızca** `scoped()` / `get_owned()` ile. Başka atölyenin kaydı → 404.
2. Sipariş durumu **yalnızca** `change_status()` → `ensure_transition()` ile değişir.
3. Para hesabı **Decimal** + `ROUND_HALF_UP`; float yasak. Sipariş anındaki fiyat kaleme dondurulur.
4. Durum değiştiren her form `csrf_token` taşır; HTMX/fetch istekleri `X-CSRF-Token` başlığıyla gönderir.
5. Şablonlarda `|safe` yasak; inline `<script>` / `style=` yasak (CSP `'self'`). Renk kodu yalnız `:root`'ta.
6. Yeni özellik = önce test (`tests/`), sonra kod. `main` korumalı: PR + CI yeşil + 1 onay.

## 5. Güvenlik checklist durumu (27 Kasım)

```
✅ Tamam : 1 (.env, varsayılansız SECRET_KEY), 2 (.gitignore), 3-4 (rol + tenant izolasyonu, IDOR testleri),
           5 (giriş/kayıt/sıfırlama rate limit), 6 (Pydantic), 7 (magic-byte, boyut, uuid ad, EXIF silme),
           8 (CORS yok = tek origin), 9 (CSP, nosniff, DENY, Referrer), 10 (Caddy HTTPS + HSTS), 11 (Argon2id),
           12 (HttpOnly/Secure/Lax), 13 (genel hata sayfası, prod'da /docs kapalı), 14 (log maskeleme),
           15 (ORM, parametreli), 16 (Jinja autoescape), 17 (HMAC + timestamp + idempotency; PayTR hash, iyzico retrieve),
           18 (OWNER/STAFF), 19 (pip-audit her PR'da), 21 (gerçek silme + anonimleştirme, bildirim geçmişi dahil),
           anahtarlar repr=False, canlı ödeme kilidi, SMTP STARTTLS sertifika doğrulaması
⚠️ Eksik : 20 (backup.sh hazır, cron + restore testi yapılacak), 22 (VPS/SMS/WhatsApp harcama alarmı),
           23 (yayın öncesi saldırgan testi), 5 (rate limit tek süreçte; çok worker'da Redis'e taşınmalı)
```

## 6. Dokümanlar

- [docs/MODUL_SAHIPLERI.md](docs/MODUL_SAHIPLERI.md): kim neyin sahibi, haftalık ritim
- [docs/KARARLAR.md](docs/KARARLAR.md): ödeme, şirket yapısı, pilot kararları
- [docs/H4_PAKET_TABLOSU.md](docs/H4_PAKET_TABLOSU.md): paket fiyatları ve H1 verisi
- Haftalık ödevler: [hafta-2](docs/odevler/hafta-2.md) · [hafta-3](docs/odevler/hafta-3.md) · [hafta-4](docs/odevler/hafta-4.md)
