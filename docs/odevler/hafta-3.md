# Hafta 3 Ödevleri (16–20 Kasım) · Uçtan uca

**Teslim:** 20 Kasım Cuma 18:00 · **Demo:** Cuma dersi, kişi başı 5 dk
**Kural:** her proje = 1 PR. `main` korumalı: PR + CI yeşil + **eşinin 1 onayı** olmadan birleşmez.

| No | Sahip | Proje | Ana dosyalar | Bağımlılık |
|---|---|---|---|---|
| PROJE 1 | Seher | Vitrin: ürün görselleri + mobil | `app/templates/public/`, `app/static/` | PROJE 7 (Alper) |
| PROJE 2 | Hayrettin | Teklif / proforma PDF | `app/modules/orders/`, `app/domain/pricing.py` | — |
| PROJE 3 | Hasan | Şifre sıfırlama (süreli token) | `app/modules/auth/` | PROJE 6 (Deha) e-posta |
| PROJE 4 | Hasan | KVKK sayfası + rıza akışı | `app/templates/`, `app/modules/customers/` | — |
| PROJE 5 | Çınar | Sürükle-bırak üretim panosu | `app/modules/orders/`, `app/static/js/` | — |
| PROJE 6 | Deha | E-posta adaptörü + bildirim geçmişi | `app/modules/notifications/` | PR #5 |
| PROJE 7 | Alper | Ürün görseli yükleme + galeri | `app/modules/media/`, `app/modules/catalog/` | PR #4 |

> **H2'den açık işin varsa önce onu bitir.** Yarım H2 üzerine H3 kurulmaz. H2 durumunu ders notunda bulabilirsin.

> **Bağımlılık okuma:** "PROJE 3 → PROJE 6" demek: Hasan'ın şifre sıfırlama e-postası, Deha'nın e-posta kanalını kullanır. Deha bitirmeden Hasan `ConsoleNotifier` ile çalışır; testler zaten gerçek e-posta göndermez.

---

## PROJE 1: Vitrin: ürün görselleri + mobil uyum
**Sahip:** Seher · **Trello:** `[Seher] H3 · Vitrinde ürün görselleri + mobil uyum` · **PR:** #6

### Kazanım
- Çok kiracılı şablon: her atölye **kendi** verisini görür, sabit içerik olmaz
- CSP altında JS: olay dinleyici (`addEventListener`) ile modal
- Paylaşılan dosyada (`app.js`) başkasının kodunu bozmadan çalışmak

### Problem
Müşteri vitrinde ürünü görüp WhatsApp'tan sipariş vermek istiyor. Kart, ürünün **kendi** adını, fiyatını ve kapak görselini göstermeli; buton **o atölyenin** numarasına gitmeli.

### Gereksinimler
- Ad, açıklama, fiyat `c.product` ve `c.price`'tan gelir; şablonda sabit ürün adı/görsel yok
- Görsel: Alper'in kapak görseli (PROJE 7). Yoksa placeholder.
- WhatsApp linki `workshop.phone`'dan; telefon yoksa buton görünmez; mesaj `|urlencode`
- Telefonda 1, tablette 2, masaüstünde 3+ sütun
- Inline `<script>`, `onclick`, `style="..."` yok

### Adım Adım Çözüm Algoritması
1. Önce **PR #3**'ü (marka) bitir; iki PR da `:root`'u değiştiriyor.
2. PR #6 dalında: `git pull origin main`, sonra `git checkout origin/main -- app/static/js/app.js`. Bu komut sipariş formunun kodunu geri getirir. Modal kodunu **ayrı bir dosyaya** taşı: `app/static/js/showcase.js`. Yalnızca `showcase.html` yüklesin: `<script src="/static/js/showcase.js" defer></script>`. Çınar da `app.js`'i değiştiriyor (PR #9); ayrı dosya çakışmayı önler.
3. Kullanılmayan görselleri sil: `git rm app/static/img/*.jpg`. Kulüp logoları satılacak üründe kullanılamaz.
4. `style="grid-column…"` → CSS'te `.showcase-empty` sınıfı.
5. WhatsApp linki:
   `https://wa.me/{{ workshop.phone|replace(' ','')|replace('+','') }}?text={{ ('Merhaba, ' ~ c.product.name ~ ' hakkında bilgi almak istiyorum.')|urlencode }}`
   Linke `rel="noopener"` ekle.
6. PROJE 7 birleşince `showcase/router.py` kart verisine `cover_url` ekle (Alper'le konuş: alan adı ne olacak?).
7. Testler (`tests/test_showcase.py`):
   - A atölyesinin vitrininde A'nın ürün adı var, B'ninki yok
   - Atölye telefonu yoksa sayfada `wa.me` geçmiyor
   - Pasif ürün vitrinde yok

### Teslim
PR #6 güncellemesi + telefon (375 px) ve masaüstü ekran görüntüsü.

---

## PROJE 2: Teklif / proforma PDF
**Sahip:** Hayrettin · **Trello:** `[Hayrettin] H3 · Teklif / proforma PDF`

### Kazanım
- Domain çıktısını (`PriceBreakdown`) belgeye dönüştürmek
- "Fiyat dondurma": teklif, **sipariş anındaki** rakamları gösterir, bugünkü has fiyatını değil
- Binary yanıt döndürmek (`Response(content=..., media_type="application/pdf")`)

### Problem
Kuyumcu müşteriye WhatsApp'tan "fiyat ne kadar?" sorusuna resmi görünen bir teklif göndermek istiyor: malzeme, işçilik, KDV ayrı ayrı, has fiyatı ve geçerlilik süresiyle.

### Gereksinimler
- `GET /siparisler/{id}/teklif.pdf` → PDF indirir (OWNER ve STAFF)
- İçerik: atölye adı ve telefonu, sipariş no, tarih, kalemler (ürün, adet, malzeme, işçilik, net), KDV, toplam, **geçerlilik: 3 gün**
- Altın ürünlerde: sipariş anındaki has gram fiyatı
- Başka atölyenin siparişi → 404

### Adım Adım Çözüm Algoritması
1. Sorun: `OrderItem` şu an sadece `unit_net`, `line_net`, `line_gross` saklıyor. Malzeme/işçilik dökümü ve has fiyatı **kaydedilmiyor**.
2. `OrderItem`'a ekle: `unit_material`, `unit_labor`, `unit_margin` (`Numeric(12,2)`, varsayılan 0), `gold_price_snapshot` (`Numeric(12,2) | None`).
3. Migration: `alembic revision --autogenerate -m "order_item price breakdown"`. Dosyayı **oku**; mevcut satırlar için `server_default="0"` gerekir.
4. `orders/service.py` → `create_order` içinde `quote()`'tan gelen dökümü bu alanlara yaz. Has fiyatı `workshop.gold_price_per_gram`'dan.
5. PDF kütüphanesi: `fpdf2` (saf Python). `requirements.txt`'e sürüm sabit ekle, `pip-audit` yeşil kalsın. Türkçe karakter için `app/static/fonts/` altındaki bir TTF'yi `add_font` ile yükle (Seher'in Inter'i kullanılabilir).
6. `orders/pdf.py` → `build_quote_pdf(order, workshop) -> bytes`. Saf fonksiyon: DB'ye dokunmaz, test etmesi kolay.
7. Router: `get_owned(db, Order, order_id, user)`, sonra `Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="teklif-{order.id}.pdf"'})`.
8. `detail.html`'e "Teklif PDF" butonu.
9. Testler (`tests/test_quote_pdf.py`):
   - Yanıt `200`, `content-type` PDF, içerik `%PDF` ile başlıyor
   - B atölyesi A'nın teklifini isterse → 404
   - Has fiyatı sonradan değişse bile kalemdeki `unit_material` aynı (fiyat dondurma)
   - `build_quote_pdf` çıktısında sipariş no geçiyor (`pypdf` ya da byte araması)

### Dikkat
- **H2'deki ürün düzenleme ekranı (PROJE 2/H2) hâlâ eksik.** Önce onu bitir: bu PDF düzenlenen ürünlerle test edilecek.

### Teslim
PR + örnek PDF (ekran görüntüsü) + test çıktısı.

---

## PROJE 3: Şifre sıfırlama (e-posta ile, süreli token)
**Sahip:** Hasan · **Trello:** `[Hasan] H3 · Şifre sıfırlama (e-posta ile, süreli token)`

### Kazanım
- Tek kullanımlık, süreli güvenlik token'ı tasarlamak
- Token'ı DB'de **hash** olarak saklamak (şifre gibi)
- "Hesap var mı?" bilgisini sızdırmamak (user enumeration)

### Problem
Atölye sahibi şifresini unuttu. E-postasına gelen linkle yeni şifre belirlemeli. Link çalınırsa da zarar sınırlı kalmalı.

### Gereksinimler
- `GET/POST /sifremi-unuttum` → cevap **her zaman** "Kayıtlıysa e-posta gönderildi"
- Link 30 dakika geçerli, tek kullanımlık
- Token DB'de `sha256` hash olarak; düz metin hiçbir yerde (DB, log) yok
- IP başına rate limit (`RateLimiter`, ör. saatte 5)
- Şifre değişince kullanıcının **tüm oturumları** silinir

### Adım Adım Çözüm Algoritması
1. Model: `PasswordReset(id, user_id, token_hash, expires_at, used_at)`. Migration üret ve oku.
2. Token: `raw = new_token()` (`core/security.py`'da var) → DB'ye `hashlib.sha256(raw.encode()).hexdigest()`.
3. POST `/sifremi-unuttum`: e-posta ile kullanıcıyı ara. **Bulsan da bulamasan da** aynı sayfayı dön. Bulursan kaydı oluştur ve link gönder: `{base_url}/sifre-yenile/{raw}`.
4. Gönderim: `request.app.state.notifier` e-posta kanalını kullanır (Deha, PROJE 6). Deha bitirene kadar `ConsoleNotifier` yeterli.
5. GET/POST `/sifre-yenile/{token}`: hash'le, kaydı bul. Süresi geçmiş ya da kullanılmışsa genel hata. Yeni şifre en az 10 karakter → `hash_password`, `used_at = now`, kullanıcının **tüm** `UserSession` kayıtlarını sil.
6. Rate limit: `app.state` üzerine `reset_limiter = RateLimiter(5, 3600)`; anahtar IP.
7. Testler (`tests/test_password_reset.py`):
   - Kayıtlı ve kayıtsız e-posta → **aynı** yanıt metni
   - Token ile şifre değişiyor → eski şifre girmiyor, yeni giriyor
   - Aynı token ikinci kez → hata
   - 31 dk sonra → hata (`expires_at`'i testte geçmişe çek)
   - Şifre değişince eski oturum çerezi → `/giris`'e yönlenir
   - DB'de token düz metin olarak yok

### Dikkat
- PR #7'deki review notu: `staff.py`'de `scoped(User, owner)` kullanımı. Bu PR'dan önce onu düzelt.

### Teslim
PR + test çıktısı + akış şeması (4 kutu yeter).

---

## PROJE 4: KVKK sayfası + açık rıza akışı
**Sahip:** Hasan · **Trello:** `[Hasan] H3 · KVKK aydınlatma sayfası + açık rıza akışı`

### Kazanım
- Hukuki metni ürüne bağlamak: metin, link, form, veri modeli
- "Bildirim izni" ile "pazarlama izni"nin farkı

### Problem
H1'de KVKK taslağı yazıldı; Trello kartında örnek metin de var. Şimdi bu metin uygulamada görünmeli ve müşterinin izni ürün içinde yönetilebilmeli.

### Gereksinimler
- `/kvkk` herkese açık sayfa; kayıt sayfasından, takip sayfasından ve vitrinden link
- Müşteri formunda iki ayrı kutu: **sipariş durumu bildirimi** ve **kampanya mesajı** (ikincisi varsayılan kapalı)
- Müşteri düzenleme ekranında izinler geri alınabiliyor; geri alınınca zaman damgası `None`
- Metinde `[ATÖLYE ADI]` gibi yer tutucular: şablonda gerçek atölye adı

### Adım Adım Çözüm Algoritması
1. Kendi H1 PDF'ini Trello'daki örnekle karşılaştır, eksikleri tamamla.
2. `app/templates/public/kvkk.html` + `GET /kvkk` (giriş gerektirmez).
3. `Customer` modeline `marketing_consent_at` ekle (migration). Mevcut `contact_consent_at` "bildirim izni" olarak kalsın.
4. Müşteri formunda iki kutu, yanında kısa metin ve `/kvkk` linki. Kutu işaretliyse zaman damgası yazılır.
5. Müşteri düzenleme: kutu kaldırılırsa ilgili alan `None`.
6. Testler:
   - `/kvkk` giriş olmadan `200`
   - Kampanya izni kapalıyken müşteri kaydı → `marketing_consent_at is None`
   - İzin geri alınınca bildirim `SKIPPED` oluyor (mevcut testi örnek al)

### Dikkat
- Metin bir **taslak**. Sayfanın altına "Son güncelleme: tarih" yaz. Satıştan önce hukukçuya okutulacak.

### Teslim
PR + `/kvkk` sayfası ve müşteri formu ekran görüntüsü.

---

## PROJE 5: Sürükle-bırak üretim panosu
**Sahip:** Çınar · **Trello:** `[Çınar] H3 · Sürükle-bırak üretim panosu`

### Kazanım
- "Arayüz izin verse de **sunucu** karar verir": state machine her zaman sunucuda
- HTML5 Drag and Drop + HTMX isteği, CSRF başlığıyla
- Hata durumunda arayüzü eski hâline döndürmek

### Problem
Usta, siparişi "Üretimde"den "Kalite kontrol"e sürükleyerek taşımak istiyor. Geçersiz bir taşıma (ör. "Alındı"dan "Teslim edildi"ye) reddedilmeli ve kart yerine dönmeli.

### Gereksinimler
- Pano kartı (`.ticket`) sürüklenip başka sütuna bırakılınca durum değişir
- Sunucu `change_status()` ve `ensure_transition()` ile karar verir; geçersizse `409` + mesaj
- Geçersizde kart eski sütuna döner, kısa uyarı çıkar
- Bildirim normal akıştaki gibi gider (`notify_status_change`)
- Inline script yok; JS `app/static/js/board.js`

### Adım Adım Çözüm Algoritması
1. Önce H2'yi bitir: çok kalemli sipariş **PR #9** (taslak), eksik backend ve testler orada yazıyor.
2. `board.html`: her sütuna `data-status="IN_PRODUCTION"`, her karta `draggable="true" data-order-id="12"`.
3. Yeni endpoint `POST /siparisler/{id}/tasi` (JSON ya da form: `to_status`). İçeride mevcut `order_status` mantığını **yeniden kullan**: kodu ortak bir fonksiyona çek, kopyalama.
4. CSRF: `base.html`'de `hx-headers` zaten `X-CSRF-Token` gönderiyor. `fetch` kullanırsan başlığı kendin ekle (`document.body.getAttribute("hx-headers")`'dan oku).
5. `board.js`: `dragstart` → id'yi sakla; `dragover` → `preventDefault`; `drop` → isteği gönder. `409` gelirse kartı eski yerine koy ve uyarı göster.
6. Mobilde sürükleme zor: sipariş detayındaki mevcut durum formu **kalsın**.
7. Testler (`tests/test_board_move.py`):
   - Geçerli taşıma → `200`, durum değişti, `OrderEvent` kaydı var
   - Geçersiz taşıma → `409`, durum aynı
   - CSRF başlığı yok → `403`
   - Başka atölyenin siparişi → `404`
   - Rızalı müşteride bildirim `notifier.sent`'e düştü

### Teslim
PR + 10 saniyelik ekran kaydı (GIF) + test çıktısı.

---

## PROJE 6: E-posta adaptörü + bildirim geçmişi ekranı
**Sahip:** Deha · **Trello:** `[Deha] H3 · E-posta adaptörü + bildirim geçmişi ekranı`

### Kazanım
- İkinci bir `Notifier` uygulaması: protokol gerçekten işe yarıyor mu?
- Kanal seçimi: müşteride telefon yoksa e-posta
- Başarısız işi tekrar denemek (retry) ve idempotent düşünmek

### Problem
Bazı müşteriler telefon yerine e-posta veriyor. Ayrıca atölye sahibi "müşteriye mesaj gitti mi?" sorusunun cevabını görmek ve gitmeyeni tekrar göndermek istiyor.

### Gereksinimler
- `EmailNotifier` (SMTP, `smtplib` + `email.message.EmailMessage`); ayarlar `.env`'den: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`
- Telefon varsa SMS/WhatsApp, yoksa e-posta, ikisi de yoksa `SKIPPED`
- Sipariş detayında "Gönderilen bildirimler" tablosu: kanal, zaman, durum
- `FAILED` satırında "Tekrar gönder" (POST + CSRF); başarılıysa durum `SENT`
- Log'da telefon ve e-posta maskeli (`core/logging.py` zaten maskeliyor; bozma)

### Adım Adım Çözüm Algoritması
1. PR #5 (SMS) birleşmeden başlama; Hasan review'unu yapsın.
2. `EmailNotifier.__init__(host, port, user, password, sender, smtp_factory=smtplib.SMTP)`: test için `smtp_factory` dışarıdan verilebilsin.
3. `send(recipient, message)`: `starttls()`, `login()`, `send_message()`. Şifre `repr`'de `***`.
4. Kanal seçimi: `notify_status_change` içinde alıcıyı seç. İki notifier tutmak için `MultiNotifier` gibi bir sınıf düşün (`sms` + `email`).
5. Geçmiş: `Notification` tablosu zaten var. `detail.html`'e `scoped(Notification, user).where(order_id == ...)` ile liste.
6. Tekrar gönder: `POST /bildirimler/{id}/tekrar`; `get_owned` ile al, yalnızca `FAILED` olanı gönder, sonucu aynı kayda yaz.
7. Testler:
   - Telefon yok, e-posta var → e-posta kanalı, `SENT`
   - Sahte SMTP hata fırlatır → `FAILED`, sipariş durumu yine değişti
   - "Tekrar gönder" → `SENT`; `SENT` bir kaydı tekrar gönderme → değişmez
   - Başka atölyenin bildirimi → `404`
   - `caplog`: e-posta adresi açık hâliyle log'da yok

### Dikkat
- PR #5'teki eksik: gerçek SMS ekran görüntüsü. Onu da PR'a ekle.
- Hasan'ın şifre sıfırlaması bu kanalı kullanacak. Fonksiyon adlarını onunla konuş.

### Teslim
PR + bildirim geçmişi ekran görüntüsü + test çıktısı.

---

## PROJE 7: Ürün görseli yükleme + galeri
**Sahip:** Alper · **Trello:** `[Alper] H3 · Ürün görseli yükleme + galeri`

### Kazanım
- H2'deki küçük resim altyapısını üründe yeniden kullanmak
- Dosya + veritabanı tutarlılığı: kayıt silinince dosya da silinir
- Başka modüle (vitrin) temiz bir arayüz vermek

### Problem
Atölye sahibi her ürüne 3–5 fotoğraf ekleyip birini kapak seçmek istiyor. Vitrin kapağı göstermeli. Silinen fotoğraf diskte yer kaplamamalı.

### Gereksinimler
- Ürün düzenleme ekranında çoklu görsel yükleme (`Media.product_id` zaten var)
- Biri **kapak**; kapak değiştirilebilir
- Silince DB kaydı **ve** orijinal + küçük resim dosyası silinir
- Vitrin için herkese açık uç: `/v/{slug}/gorsel/{id}?boyut=kucuk` (yalnızca o atölyenin, aktif ürünün görseli)
- Başka atölyenin görseli → 404

### Adım Adım Çözüm Algoritması
1. PR #4 (küçük resim) birleşmeden başlama; Seher review'unu yapsın.
2. `Media`'ya `is_cover: bool` ekle (migration). Bir üründe en fazla bir kapak: kapak seçilince diğerlerini `False` yap (aynı transaction).
3. `POST /urunler/{id}/gorsel` (OWNER, CSRF): `save_image` → `Media(product_id=...)`.
4. `POST /gorsel/{id}/kapak` ve `POST /gorsel/{id}/sil`: `get_owned`. Silmede önce DB commit, sonra dosyalar; dosya yoksa hata verme (`missing_ok=True`).
5. Vitrin ucu: slug'dan atölye, `Media.workshop_id == ws.id`, ürün aktif ve `is_public`. Değilse 404.
6. Seher'e arayüz ver: `cover_url(product) -> str | None` yardımcı fonksiyonu. Vitrin şablonu bunu kullanır.
7. Testler (`tests/test_product_gallery.py`):
   - 3 görsel yükle, ikincisini kapak yap → kapak sadece o
   - Sil → DB'de yok, diskte orijinal ve `_t` dosyası yok
   - B atölyesi A'nın görselini kapak/sil yapamaz → 404
   - Pasif ürünün görseli vitrinde → 404

### Dikkat
- H1 araştırma kartın (rakiplerin fotoğraf/video akışı) hâlâ boş. 1 sayfalık özetini ekle; H4'teki video işi ona dayanacak.

### Teslim
PR + galeri ve vitrin ekran görüntüsü + test çıktısı.

---

## Herkes için hatırlatma (H2'den öğrendiklerimiz)

| Ne oldu | Ders |
|---|---|
| Ortak dosyanın (`app.js`) içeriği tamamen değiştirildi, başka ekran bozuldu | Sayfaya özel JS ayrı dosyada (`showcase.js`, `board.js`). Paylaşılan dosyaya dokunduysan `git diff` ile ne sildiğine bak. |
| Zip Trello'ya yüklendi, PR açılmadı | Teslim **PR**'dır. Collaborator'sun: `git push` + PR aç (H2 PROJE 7). |
| Şablonda sıraya göre sabit içerik (`loop.index == 1`) | Çok kiracılı üründe her şey veriden gelir. |
| Kod iyiydi ama `scoped()` yerine elle filtre | Altın kurallar herkes için aynı; review'da ilk bakılan yer. |
| İki PR aynı satırı değiştirdi, çakıştı | Küçük PR, sık `git pull origin main`. |
