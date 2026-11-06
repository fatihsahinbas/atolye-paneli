# Hafta 2 Ödevleri (9–13 Kasım)

**Teslim:** 13 Kasım Cuma 18:00 · **Demo:** Cuma dersi, kişi başı 5 dk
**Kural:** her proje = 1 PR. CI yeşil değilse PR birleştirilmez.

| No | Sahip | Proje | Ana dosyalar |
|---|---|---|---|
| PROJE 1 | Seher | Marka ve tema | `app/static/css/app.css`, `app/templates/base.html` |
| PROJE 2 | Hayrettin | Ürün düzenleme ve pasife alma | `app/modules/catalog/` |
| PROJE 3 | Hasan | Personel (STAFF) yönetimi | `app/modules/auth/` |
| PROJE 4 | Çınar | Çok kalemli sipariş formu | `app/modules/orders/` |
| PROJE 5 | Deha | İlk gerçek bildirim adaptörü | `app/modules/notifications/` |
| PROJE 6 | Alper | Küçük resim + EXIF temizleme | `app/modules/media/` |
| PROJE 7 | Herkes | Git akışı ve ilk PR | `.github/pull_request_template.md` |

> Önce **PROJE 7**'yi oku: diğer altı projenin nasıl teslim edileceğini anlatıyor.

---

## PROJE 1: Marka ve tema
**Sahip:** Seher · **Trello:** `[Seher] H2 · Marka: renk paleti, logo, yazı tipi`

### Kazanım
- CSS değişkenleriyle (custom properties) tek noktadan tema yönetimi
- Erişilebilir renk kontrastı (WCAG AA)
- CSP (Content-Security-Policy) altında font ve görsel kullanma

### Problem
Uygulama şu an "geçici" kahverengi tonlarla çalışıyor. Pilot atölyelere gösterilecek, güven veren ve kendi kimliği olan bir görünüm gerekiyor. Görüşmelerden öğrendiğin şey: atölye sahipleri ürünü nasıl hissetmeli?

### Gereksinimler
- Logo (SVG) + 5–6 renklik palet + yazı tipi kararı
- Tüm renkler `:root` değişkenlerinden gelir; CSS'te başka yerde sabit renk kodu yok
- Metin/arka plan kontrastı en az **4.5:1**
- Telefon genişliğinde (375 px) hiçbir sayfa taşmıyor
- Inline `style="..."` ve inline `<script>` yok (CSP bunları engeller)

### Adım Adım Çözüm Algoritması
1. H1 görüşme notlarından ürünü anlatan **3 sıfat** seç (ör. "güvenilir, sıcak, zanaatkâr").
2. Bu sıfatlara göre palet seç: 1 ana renk, 1 vurgu, 1 koyu metin, 1 açık zemin, 1 başarı, 1 hata.
3. Her metin/zemin çiftinin kontrastını ölç (ör. WebAIM Contrast Checker). 4.5:1 altını düzelt.
4. `app/static/css/app.css` içindeki `:root` bloğunu yeni değerlerle güncelle.
5. Dosyada kalan sabit renk kodlarını (`#...`) bul (`grep -n "#[0-9a-fA-F]\{3,6\}" app/static/css/app.css`) ve değişkene çevir.
6. Logoyu `app/static/img/logo.svg` olarak ekle. `base.html`'de `◆ Atölye Paneli` metninin yerine `<img src="/static/img/logo.svg" alt="Atölye Paneli">` koy.
7. **Yazı tipi:** Google Fonts linki CSP'ye takılır (`style-src 'self'`). İki seçeneğin var:
   - sistem font yığını (hiç dosya yok, en hızlı), ya da
   - `.woff2` dosyasını `app/static/fonts/` altına koyup `@font-face` ile yüklemek (lisansı kontrol et).
8. Tarayıcıda giriş, pano, sipariş detayı, takip ve vitrin sayfalarını aç. DevTools → mobil görünüm (375 px) ile kontrol et.
9. DevTools Console'da kırmızı CSP hatası olmadığını doğrula.

### Dikkat
- Ürün adı Cuma oylamasıyla değişebilir. Logoyu isimden bağımsız bir sembol + yazı olarak tasarla.

### Teslim
PR açıklamasına **önce/sonra ekran görüntüleri** (masaüstü + mobil) ve palet tablosu (renk, değişken adı, kontrast oranı).

---

## PROJE 2: Ürün düzenleme ve pasife alma
**Sahip:** Hayrettin · **Trello:** `[Hayrettin] H2 · Ürün düzenleme ve pasife alma ekranı`

### Kazanım
- Tenant güvenliğiyle uçtan uca güncelleme (Update) akışı
- "Silme yerine pasife alma": eski siparişler neden bozulmamalı?
- Form ayrıştırma kodunu yeniden kullanılabilir yapmak (refactor)

### Problem
Kuyumcu bir ürünün gramını ya da işçilik milyemini değiştirmek istiyor. Satıştan kalkan ürünü de listeden kaldırmak istiyor. Ama o ürünle verilmiş eski siparişlerin tutarı değişmemeli.

### Gereksinimler
- `GET /urunler/{id}/duzenle` → dolu form
- `POST /urunler/{id}` → güncelle (aynı doğrulama kuralları: `ProductIn`)
- `POST /urunler/{id}/pasif` ve `POST /urunler/{id}/aktif`
- Sadece **OWNER** yapabilir. STAFF → 403. Başka atölyenin ürünü → 404.
- Pasif ürün sipariş formunda ve vitrinde **görünmez**, ürün listesinde "Pasif" etiketiyle görünür.

### Adım Adım Çözüm Algoritması
1. `catalog/router.py` içindeki `create_product` fonksiyonuna bak. Form alanlarını `ProductIn`'e çeviren kısmı `_parse_product_form(...) -> ProductIn` adlı yardımcı fonksiyona taşı. `create_product` bu fonksiyonu kullansın. **Testler hâlâ yeşil olmalı:** refactor davranışı değiştirmez.
2. `GET /urunler/{product_id}/duzenle` ekle:
   - `user: User = Depends(require_owner)`
   - `product = get_owned(db, Product, product_id, user)`: başka atölyeninkiyse otomatik 404
   - `catalog/edit.html` şablonunu ürün değerleriyle doldur
3. `POST /urunler/{product_id}` ekle: `dependencies=[Depends(csrf_protect)]`, `_parse_product_form` ile doğrula, alanları `product` nesnesine yaz, `db.commit()`.
4. `POST /urunler/{product_id}/pasif` ve `/aktif` ekle: sadece `product.is_active` değişir.
5. Sipariş formu zaten `Product.is_active.is_(True)` ile filtreliyor. Vitrin (`showcase/router.py`) de filtreliyor. **Doğrula**, varsayma.
6. `catalog/list.html`'e her satır için "Düzenle" linki ve "Pasife al / Aktif et" formu (CSRF token ile) ekle.
7. Testleri yaz (`tests/test_catalog.py`):
   - OWNER ürünü düzenler → yeni fiyat listede görünür
   - STAFF düzenlemeye çalışır → 403
   - B atölyesi A'nın ürününü düzenlemeye çalışır → 404
   - Pasif ürün `/siparisler/yeni` sayfasında ve `/v/{slug}` vitrininde yok
   - Ürün fiyatı değişti → **eski siparişin tutarı aynı** (fiyat dondurma)

### Bonus (H1 görüşmelerine göre)
Kuyumcular işçiliği "gram başı TL" olarak hesaplıyorsa:
- `Product`'a `labor_per_gram: Decimal | None` alanı ekle
- `alembic revision --autogenerate -m "labor_per_gram"`: CI'daki `alembic check` migration'sız PR'ı yakalar
- `domain/pricing.py`'a hesap + test (Decimal, float yok)

### Teslim
PR + test çıktısı + düzenleme ekranının görüntüsü.

---

## PROJE 3: Personel (STAFF) yönetimi
**Sahip:** Hasan · **Trello:** `[Hasan] H2 · Personel (STAFF) ekleme ve yönetimi`

### Kazanım
- Rol tabanlı yetki (RBAC) ve "en az yetki" ilkesi
- Geçici şifre ve ilk girişte zorunlu şifre değişimi
- Hesap pasife alınınca açık oturumları anında düşürmek

### Problem
Atölye sahibi, ustasının siparişleri görmesini ve durum değiştirmesini istiyor. Ama usta fiyatları ve ürünleri değiştirememeli. Usta işten ayrılırsa erişimi o an kesilmeli.

### Gereksinimler
- `GET /personel` (OWNER): atölyenin kullanıcı listesi
- `POST /personel` (OWNER): ad + e-posta → STAFF hesabı + **tek seferlik gösterilen** geçici şifre
- STAFF ilk girişte şifresini değiştirmeden başka sayfaya geçemez
- `POST /personel/{id}/pasif`: kullanıcı pasif + **tüm oturumları silinir**
- OWNER kendini pasife alamaz

### Adım Adım Çözüm Algoritması
1. `User` modeline `must_change_password: Mapped[bool] = mapped_column(default=False)` ekle.
2. Migration üret: `alembic revision --autogenerate -m "user must_change_password"`. Oluşan dosyayı **oku**; `server_default` gerekiyorsa ekle (mevcut satırlar için).
3. `auth/router.py`'a `GET/POST /personel` ekle (`require_owner`). Listeyi `scoped(User, user)` ile çek: tenant filtresi.
4. Ekleme:
   - Pydantic şeması: `StaffIn(full_name, email)`, `auth/schemas.py`'daki e-posta doğrulamasını kullan
   - `temp = secrets.token_urlsafe(9)` → `hash_password(temp)` → `role=Role.STAFF`, `must_change_password=True`
   - E-posta zaten varsa **genel hata** ver ("Kayıt tamamlanamadı"): hangi e-postanın kayıtlı olduğu sızmasın
   - Geçici şifreyi **sadece bir kez** sayfada göster. Log'a yazma, DB'ye düz metin yazma.
5. Zorunlu şifre değişimi:
   - `GET/POST /hesap/sifre`: eski şifre + yeni şifre (en az 10 karakter)
   - `core/deps.py` → `current_user` içinde: `user.must_change_password` ve istek `/hesap/sifre` ya da `/cikis` değilse → `/hesap/sifre`'ye yönlendir (ipucu: `LoginRequired` gibi yeni bir istisna + `main.py`'da handler)
6. Pasife alma: `user.is_active = False` + `delete(UserSession).where(UserSession.user_id == id)`. `load_session` zaten pasif kullanıcıyı reddediyor; oturumları silmek ikinci güvence.
7. Testler (`tests/test_staff.py`):
   - OWNER personel ekler → STAFF geçici şifreyle girer → `/` yerine `/hesap/sifre`'ye yönlenir
   - STAFF `/urunler`'e POST → 403, `/personel` → 403
   - B atölyesinin OWNER'ı A'nın personelini göremez / pasife alamaz → 404
   - Pasife alınan kullanıcının **eski çerezi** artık çalışmaz
   - OWNER kendini pasife alamaz

### Teslim
PR + test çıktısı + yetki matrisi tablosu (hangi rol hangi sayfayı görebilir) PR açıklamasında.

---

## PROJE 4: Çok kalemli sipariş formu
**Sahip:** Çınar · **Trello:** `[Çınar] H2 · Çok kalemli sipariş formu`

### Kazanım
- Aynı isimli çoklu form alanlarını (`list[int] = Form(...)`) işlemek
- HTMX ile dinamik satır ekleme (sunucu HTML parçası döner)
- Girdi doğrulamada sınır değerler: boş liste, uzunluk uyuşmazlığı, üst sınır

### Problem
Müşteri bir siparişte "1 bilezik + 2 isimli kolye + 1 filografi tablo" istiyor. Şu an her ürün için ayrı sipariş açmak gerekiyor.

### Gereksinimler
- "+ Kalem ekle" ile yeni satır (ürün + adet + açıklama); her satırda "Sil"
- En az 1, en fazla 20 kalem
- Kaydedince tek sipariş, çok kalem; toplam = kalemlerin toplamı
- Başka atölyenin ürünü tek bir satırda bile olsa → 404, sipariş oluşmaz

### Adım Adım Çözüm Algoritması
1. `orders/service.py` → `create_order(...)` zaten `list[NewItem]` alıyor. **Servise dokunmadan** başla; değişen router ve şablon.
2. Satır şablonunu ayır: `app/templates/orders/_item_row.html` (ürün `<select name="product_id">`, `<input name="quantity">`, `<input name="description">`, "Sil" butonu `class="remove-row"`).
3. `GET /siparisler/kalem-satiri` endpoint'i: sadece `_item_row.html` döner (ürün listesiyle). GET olduğu için CSRF gerekmez.
4. `new.html`'de satırları `<div id="items">` içine koy. "+ Kalem ekle" butonu:
   `hx-get="/siparisler/kalem-satiri" hx-target="#items" hx-swap="beforeend"`
5. "Sil" butonu: inline `onclick` **yasak** (CSP). `app/static/js/app.js`'e olay delegasyonu ekle:
   `document.addEventListener("click", e => { if (e.target.matches(".remove-row")) ... })`
6. Router'da POST imzasını değiştir:
   `product_id: list[int] = Form(...)`, `quantity: list[int] = Form(...)`, `description: list[str] = Form(...)`
7. Doğrula: üç listenin uzunluğu eşit mi, 1–20 arası mı, her adet 1–1000 mi? Değilse formu hata mesajıyla geri göster.
8. `zip(...)` ile `NewItem` listesine çevir → `create_order`.
9. Fiyat önizlemesi: mevcut tek ürünlük önizlemeyi satır bazına taşı ya da toplam için yeni bir endpoint yaz (seçim senin, PR'da gerekçesini yaz).
10. Testler (`tests/test_orders_multi.py`):
    - 3 kalem → `total_gross` = kalemlerin toplamı
    - Uzunluk uyuşmazlığı → hata, sipariş yok
    - 21 kalem → hata
    - 2. satırda başka atölyenin ürünü → 404, **hiç sipariş oluşmamış** (DB'yi say)

### Ayrı PR (varsa)
H1 akış şemasından çıkan yeni durum önerin (ör. "kapora bekleniyor") **ayrı PR** olsun: `domain/order_status.py` + testleri.

### Teslim
PR + 3 kalemli sipariş ekran görüntüsü + test çıktısı.

---

## PROJE 5: İlk gerçek bildirim adaptörü
**Sahip:** Deha · **Trello:** `[Deha] H2 · İlk gerçek bildirim adaptörü (WhatsApp ya da SMS)`

### Kazanım
- Protokol (interface) arkasına dış servis bağlamak: "Bağımlılığı tersine çevir"
- Dış servisi **gerçek ağa çıkmadan** test etmek (`httpx.MockTransport`)
- API anahtarını güvenli yönetmek ve log'a sızdırmamak

### Problem
Sipariş durumu değişince müşteriye gerçek mesaj gitmeli. H1'de seçtiğin sağlayıcıyı bağla. Sağlayıcı çökse bile atölyenin işi durmamalı.

### Gereksinimler
- `Notifier` protokolünü uygulayan yeni sınıf (ör. `SmsNotifier` / `WhatsAppNotifier`)
- Kanal `.env`'den seçilir: `NOTIFY_CHANNEL=console|sms|whatsapp`
- API anahtarı sadece `.env`'de; kodda, testte, log'da görünmez
- Sağlayıcı hata verirse: bildirim `FAILED`, sipariş durumu **yine değişir**
- Rıza yoksa hiç istek atılmaz (`SKIPPED`)

### Adım Adım Çözüm Algoritması
1. `notifications/service.py`'daki `Notifier` protokolünü ve `ConsoleNotifier`'ı oku. Yeni sınıfın aynı iki şeye sahip olmalı: `channel` ve `send(recipient, message)`.
2. `core/config.py`'a alanlar ekle: `notify_channel: str = "console"`, `sms_api_url: str = ""`, `sms_api_key: str = ""` (sağlayıcına göre adlandır). `.env.example`'a boş olarak ekle.
3. `httpx`'i `requirements.txt`'e taşı (şu an sadece dev'de). Sürümü sabitle.
4. Sınıfı yaz:
   - `__init__(self, api_url, api_key, client: httpx.Client | None = None)`: **client dışarıdan verilebilsin** (test için)
   - `send`: telefonu `+90XXXXXXXXXX` biçimine çevir → `client.post(..., timeout=5)` → 2xx değilse istisna fırlat
5. Fabrika: `build_notifier(settings) -> Notifier`. `main.py`'da `notifier or ConsoleNotifier()` yerine `notifier or build_notifier(settings)`.
6. `notify_status_change` zaten istisnayı yakalayıp `FAILED` yazıyor. **Bunu bozma**, testle kanıtla.
7. Testler (`tests/test_notifier_sms.py`), gerçek ağ yok:
   - `httpx.MockTransport(lambda req: httpx.Response(200))` → `SENT`
   - `httpx.Response(500)` → `FAILED` + sipariş durumu yine değişmiş
   - Telefon `0532 111 22 33` → istekte `+905321112233`
   - `caplog` ile: API anahtarı log'da **yok**
8. Gerçek sağlayıcıyla **bir kez** elle dene (kendi telefonuna). Ekran görüntüsünü PR'a koy; anahtarı koyma.

### Dikkat
- Toplu SMS / ticari ileti kuralları (İYS vb.) H1 araştırmanda çıktıysa PR açıklamasına not düş.
- Gönderim şu an istek içinde, senkron. İleride kuyruk/outbox işçisine taşınacak; şimdilik `timeout=5` yeterli.

### Teslim
PR + mock testleri + gerçek gönderim ekran görüntüsü.

---

## PROJE 6: Küçük resim (thumbnail) + EXIF temizleme
**Sahip:** Alper · **Trello:** `[Alper] H2 · Yüklenen fotoğraftan küçük resim (thumbnail) üretimi`

### Kazanım
- Pillow ile görüntü işleme: doğrulama, döndürme, yeniden boyutlandırma
- Gizlilik: telefon fotoğrafındaki **GPS konumu** EXIF'te saklanır, müşteriye sızmamalı
- Bozuk/kötü niyetli dosyaya karşı savunma (decompression bomb)

### Problem
Usta telefonla üretim fotoğrafı çekip yüklüyor: 4 MB, yan yatmış, içinde atölyenin GPS konumu var. Galeri yavaş açılıyor ve müşteri takip sayfasında fotoğrafı indirince konum bilgisini de alıyor.

### Gereksinimler
- Her yüklemede orijinal **yeniden kodlanarak** saklanır (EXIF yok) + en fazla 400 px küçük resim
- Telefon yönü (EXIF orientation) doğru uygulanır
- Magic byte'ı doğru ama içi bozuk dosya → 400 hata, **500 değil**
- Galeri küçük resmi, tıklanınca orijinali gösterir

### Adım Adım Çözüm Algoritması
1. `Pillow`'u `requirements.txt`'e ekle (sürüm sabit). `pip-audit` yeşil kalsın.
2. `media/service.py` → `save_image` içinde, magic byte kontrolünden **sonra**:
   - `Image.MAX_IMAGE_PIXELS = 40_000_000` (dev boyutlu "bomba" görsellere sınır)
   - `img = Image.open(BytesIO(data)); img.verify()` → bozuksa `UploadError`
   - `verify()` sonrası dosyayı **yeniden aç** (Pillow kuralı)
   - `img = ImageOps.exif_transpose(img)`: yönü düzelt
3. Orijinali EXIF'siz kaydet: `img.save(path, format=..., exif=b"")` (JPEG için `quality=85`).
4. Küçük resim: `thumb = img.copy(); thumb.thumbnail((400, 400))` → `{uuid}_t.webp`.
5. İsimlendirme kuralı: migration gerekmesin diye küçük resim adı `stored_name`'den türetilir. `media_path` için `thumb_name(stored_name)` yardımcı fonksiyonu yaz; path traversal kontrolü onda da çalışsın.
6. Endpoint'ler: `/medya/{id}?boyut=kucuk` ve `/t/{kod}/medya/{id}?boyut=kucuk`. Şablonlarda galeri `<img>`'i küçüğü, `<a href>` orijinali göstersin.
7. ⚠️ **Mevcut testi güncelle:** `tests/test_orders_tenancy.py` içindeki `PNG = b"\x89PNG..." + sıfırlar` gerçek bir görsel değil. Pillow doğrulaması bunu reddedecek. Testte Pillow ile gerçek küçük bir PNG üret:
   `buf = BytesIO(); Image.new("RGB", (800, 600), "red").save(buf, "PNG")`
8. Yeni testler (`tests/test_media.py`):
   - GPS EXIF'li JPEG yükle → kaydedilen dosyada EXIF **yok**
   - 3000×2000 görsel → küçük resim en fazla 400 px
   - Magic byte'ı doğru, içi çöp dosya → 400
   - Başka atölye küçük resme de erişemez → 404

### Teslim
PR + önce/sonra dosya boyutu karşılaştırması + EXIF testinin çıktısı.

---

## PROJE 7: Git akışı ve ilk PR (herkes)
**Sahip:** Herkes · Diğer altı projenin teslim yolu

### Kazanım
- Dal (branch) → commit → push → PR → CI → review → merge döngüsü
- İyi commit mesajı ve iyi PR açıklaması yazmak
- Kırmızı CI'ı okuyup düzeltmek

### Kurallar
- `main`'e doğrudan push **yok**. Her iş kendi dalında.
- Dal adı: `isim/kisa-aciklama`. Örnek: `cinar/cok-kalemli-siparis`
- Küçük PR, hızlı review: 400 satırı geçen PR'ı böl.

### Adım Adım Çözüm Algoritması
1. Güncel kodu al: `git checkout main && git pull`
2. Dal aç: `git checkout -b seher/marka-tema`
3. Küçük adımlarla çalış; her mantıklı adımda commit:
   `git add -p` (ne eklediğini gör) → `git commit -m "Tema renkleri CSS değişkenlerine taşındı"`
   Commit mesajı: **ne değişti**, Türkçe, emir kipinde ya da geçmiş zamanda, 72 karakteri geçmesin.
4. Push etmeden önce yerelde CI'ın aynısını çalıştır:
   `ruff check . && pytest -q`
   Modeli değiştirdiysen: `alembic revision --autogenerate -m "..."` ve oluşan dosyayı oku.
5. `git push -u origin seher/marka-tema`
6. GitHub'da **Compare & pull request** → şablon kendiliğinden gelir (`.github/pull_request_template.md`). Doldur.
7. CI'ı bekle: yeşil ✓ ise Trello kartını **Review**'a taşı, PR linkini karta ekle.
   Kırmızı ✗ ise: **Details** → hangi adım patladı? → düzelt → aynı dala tekrar push (PR kendiliğinden güncellenir).
8. Review yorumlarına cevap ver, düzeltmeyi push et, yorumu "Resolve" et.
9. Fatih hoca onaylayıp merge edince kartın **Demo**'ya geçer. Cuma göster.

### Sık hatalar
| Belirti | Neden | Çözüm |
|---|---|---|
| `ruff` kırmızı | Kullanılmayan import, uzun satır | `ruff check . --fix` |
| `alembic check` kırmızı | Model değişti, migration yok | `alembic revision --autogenerate -m "..."` |
| Test yerelde yeşil, CI'da kırmızı | `.env`'ye ya da yerel dosyaya bağımlılık | Testte ayarları `Settings(...)` ile ver (bkz. `tests/conftest.py`) |
| PR'da "conflicts" | Başkası aynı dosyayı değiştirdi | `git pull origin main` → çakışmayı düzelt → commit → push |

### Teslim
Bu hafta herkesin **en az 1 birleşmiş PR'ı** olmalı.
