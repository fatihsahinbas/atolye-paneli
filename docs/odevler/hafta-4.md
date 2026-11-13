# Hafta 4 Ödevleri (23–27 Kasım) · Canlıya hazırlık

**Teslim:** 27 Kasım Cuma 18:00 · **Demo:** Cuma dersi, kişi başı 5 dk
**Kural:** her proje = 1 PR. `main` korumalı: PR + CI yeşil + **eşinin 1 onayı** olmadan birleşmez.

| No | Sahip | Proje | Ana dosyalar | Bağımlılık |
|---|---|---|---|---|
| PROJE 1 | Hasan | Abonelik ödemesi: iyzico + PayTR adaptörü (**test ortamı**) | `app/domain/subscription.py`, `app/modules/payments/` | PROJE 3 (`plans.py`) |
| PROJE 2 | Seher | Atölye ayarları ekranı (telefon) + pilot kurulumu | `app/modules/workshop/`, `app/templates/workshop/` | — |
| PROJE 3 | Hayrettin | Paket tanımları + fiyatlandırma sayfası | `app/domain/plans.py`, `app/templates/public/` | — |
| PROJE 4 | Çınar | Termin hesabı + gecikme uyarısı | `app/domain/deadline.py`, `app/modules/orders/` | PR #9, H3 pano |
| PROJE 5 | Deha | Lansman içerik planı | Trello kartı | H3 e-posta |
| PROJE 6 | Alper | Takip sayfasında "ürününüz yapılıyor" videosu | `app/modules/media/`, `app/modules/tracking/` | H3 galeri |

> **Bu haftanın kararları** (`docs/KARARLAR.md`, 13 Kasım): Şirket ya da fatura yapısı kurulmuyor. Ödeme **yalnızca test ortamında** (sandbox) çalışır, gerçek para alınmaz. Pilot atölyeler **ücretsiz** kullanır. Demo hedefi: abonelik başlat → test kartıyla öde → abonelik uzadı.

> **Önce açık işini bitir.** H2 ya da H3'ten açık işin varsa H4'e ondan sonra geç. Bir halka gecikirse **kapsam küçülür, tarih kaymaz**: bu hafta yetişmeyen kısım H5'e kalır, demo günü değişmez.

> **Bağımlılık okuma:** "PROJE 1 → PROJE 3" demek: Hasan ödeme tutarını Hayrettin'in `plans.py` dosyasından okur. Hangisi önce başlarsa dosyayı aşağıdaki **imzayla** açar, diğeri üstüne ekler.

---

## Ortak arayüz: `app/domain/plans.py`
Hasan ile Hayrettin bu dosyada buluşur. Saf Python: DB, FastAPI, ayar yok.

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Plan:
    code: str                         # "BASLANGIC", "ATOLYE", "PILOT"
    name: str                         # ekranda görünen ad
    monthly_price: Decimal            # KDV dahil, TL
    max_orders_per_month: int | None  # None = sınırsız


PILOT = Plan("PILOT", "Pilot (ücretsiz)", Decimal("0"), None)
PLANS: dict[str, Plan] = {p.code: p for p in [PILOT]}  # Hayrettin paketleri ekler


def get_plan(code: str) -> Plan:
    try:
        return PLANS[code]
    except KeyError:
        raise ValueError(f"Bilinmeyen paket: {code}") from None
```

---

## PROJE 1: Abonelik ödemesi: iyzico + PayTR (test ortamı)
**Sahip:** Hasan · **Eş:** Deha · **Trello:** `[Hasan] H4 · Abonelik ödemesi (iyzico / PayTR)`

### Kazanım
- **Bir protokol, iki uygulama:** `Notifier`'da (SMS + WhatsApp) gördüğün deseni ödemede kurmak. Sağlayıcı değişince iş kodu değişmez.
- Kart bilgisine hiç dokunmamak: ödeme formu sağlayıcının sayfasında açılır.
- Sağlayıcıdan gelen sonuca **güvenmeden önce doğrulamak**: iyzico'da sunucudan sorgu, PayTR'de HMAC imza.
- İdempotency: aynı ödeme bildirimi iki kez gelirse abonelik iki kez uzamaz.

### Problem
Atölye sahibi "Abonelik" sayfasında paketini görüp "Öde"ye basar, test kartıyla öder ve aboneliğinin bitiş tarihi bir ay uzar. Hangi sağlayıcının kullanılacağı `.env`'deki tek bir ayarla seçilir: `PAYMENT_PROVIDER=fake|iyzico|paytr`. Pilot atölyeler ödeme ekranı görmez.

### Gereksinimler
- `PaymentProvider` protokolü + üç uygulama: `FakeProvider` (test ve anahtarsız demo), `IyzicoProvider`, `PaytrProvider`
- Anahtarlar yalnızca `.env`'de, `Field(repr=False)`; log'da görünmez
- **Canlı ödeme kilidi:** `PAYMENT_LIVE=false` (varsayılan) iken iyzico adresi `sandbox-api.iyzipay.com` değilse ya da PayTR `test_mode` 1 değilse uygulama **açılmaz**
- Tutar `Decimal`; kuruşa çevirirken `ROUND_HALF_UP`. Bildirimdeki tutar bizim kayıttaki tutarla eşleşmiyorsa abonelik uzamaz.
- Aynı bildirim iki kez gelirse ikinci çağrı hiçbir şeyi değiştirmez
- Pilot atölye (`is_pilot=True`): ödeme butonu yok, "Pilot programı: ücretsiz" yazar
- Yeni kayıt olan atölyeye 14 günlük deneme süresi (`subscription_ends_at = now + 14 gün`)
- Süresi biten atölyede üst bantta uyarı. **Engelleme H5'te** (bu hafta yalnızca uyarı).

### Akış
| Adım | iyzico (Checkout Form) | PayTR (iFrame API) |
|---|---|---|
| 1. Başlat | `POST /abonelik/baslat` → `Payment(PENDING)` → SDK `CheckoutFormInitialize` → `paymentPageUrl`'e **303** | Aynı uç → `get-token` isteği → iframe sayfası (`https://www.paytr.com/odeme/guvenli/{token}`) |
| 2. Ödeme | Kullanıcı iyzico sayfasında test kartını girer | Kullanıcı iframe içinde test kartını girer |
| 3. Sonuç bize nasıl gelir | Tarayıcı `callbackUrl`'e **POST** eder: içinde yalnızca `token` var | PayTR sunucusu "Bildirim URL"ine **POST** eder: `merchant_oid`, `status`, `total_amount`, `hash` |
| 4. Doğrulama | `token` ile `CheckoutForm.retrieve` → `paymentStatus == "SUCCESS"` ve `paidPrice` | `hash == base64(hmac_sha256(merchant_key, merchant_oid + merchant_salt + status + total_amount))` |
| 5. Cevap | Kullanıcıyı `/abonelik?sonuc=ok` sayfasına 303 | Düz metin **`OK`** (başka hiçbir şey yazılmaz, yoksa PayTR tekrar dener) |

### Adım Adım Çözüm Algoritması
1. **Önce açık işler:** PR #7 review notu (`staff.py`'de elle `workshop_id` filtresi → `scoped()`) ve H3 KVKK sayfası. Ödeme işine sonra başla.
2. **Domain** (`app/domain/subscription.py`, saf Python, önce test):
   - `add_months(dt, n)`: ay sonuna kırpar. 31 Ocak + 1 ay → 28 (ya da 29) Şubat.
   - `extend(current_end, now, months)`: Abonelik hâlâ geçerliyse **bitiş tarihinden**, bitmişse **şimdiden** itibaren uzatır. Erken ödeyen kullanıcı gün kaybetmez.
   - `is_active(ends_at, now, is_pilot) -> bool`
3. **Model:**
   - `Workshop`'a ekle: `plan_code` (`String(20)`, varsayılan `"PILOT"`), `subscription_ends_at` (`DateTime(timezone=True) | None`), `is_pilot` (`bool`, varsayılan `False`).
   - Yeni model `Payment(TenantMixin)`: `merchant_oid` (unique, **yalnızca harf ve rakam**; PayTR başka karakter kabul etmez), `provider`, `plan_code`, `months`, `amount` (`Numeric(12,2)`), `status` (`PENDING/PAID/FAILED`), `provider_ref` (iyzico token), `paid_at`.
   - Migration'ı üret ve **oku**. Son head `5b9916c3a44e`'ye bağlanmalı; mevcut atölyeler için `server_default` ver.
4. **Protokol** (`app/modules/payments/providers.py`):
   ```python
   @dataclass(frozen=True)
   class CheckoutRequest:
       merchant_oid: str
       amount: Decimal
       description: str
       buyer_email: str
       buyer_name: str
       buyer_ip: str
       callback_url: str   # iyzico'nun tarayıcıyı döndüreceği adres
       ok_url: str         # PayTR başarı / hata sayfaları
       fail_url: str

   @dataclass(frozen=True)
   class CheckoutStart:
       redirect_url: str | None = None  # iyzico
       iframe_url: str | None = None    # PayTR
       provider_ref: str = ""           # iyzico token (dönüşte Payment'ı bulmak için)

   @dataclass(frozen=True)
   class PaymentResult:
       merchant_oid: str
       success: bool
       amount: Decimal
       provider_ref: str = ""

   class PaymentProvider(Protocol):
       name: str
       def start(self, req: CheckoutRequest) -> CheckoutStart: ...
   ```
   Doğrulama sağlayıcıya özeldir, protokole koyma: `IyzicoProvider.retrieve(token) -> PaymentResult` ve `PaytrProvider.verify_notification(form) -> PaymentResult` (imza yanlışsa `InvalidSignature` fırlatır).
5. **Ortak iş kuralı** (`payments/service.py`): `apply_result(db, result) -> Payment`
   - `merchant_oid` ile `Payment`'ı bul; yoksa `None` dön.
   - Zaten `PAID` ise **hiçbir şey yapma** (idempotency).
   - `result.amount != payment.amount` ise `FAILED`, log'a uyarı, abonelik uzamaz.
   - Başarılıysa `PAID`, `paid_at`, `ws.subscription_ends_at = extend(...)`, `ws.plan_code = payment.plan_code`. **Tek commit.**
6. **iyzico:** Resmi SDK'yı kullan: `iyzipay==1.0.46` (`requirements.txt`'e sabit sürümle ekle, `pip-audit` yeşil kalsın).
   - Testte SDK'yı dışarıdan verebilmek için: `IyzicoProvider(api_key, secret_key, base_url, sdk=iyzipay)`.
   - Alıcı bilgilerinde TC kimlik numarası **sorma**: test ortamında `"11111111111"` yeterli (KVKK).
   - Dönüş ucu `POST /odeme/iyzico/donus`. **Dikkat:** Bu istek iyzico'nun sayfasından gelir. Oturum çerezimiz `SameSite=Lax` olduğu için çerez gönderilmez; kullanıcı "giriş yapmamış" görünür. Bu yüzden ucu `current_user`'a bağlama. `Payment`'ı `provider_ref == token` ile bul, işi bitir, `/abonelik?sonuc=...`'ya 303 dön. O GET isteğinde çerez gelir.
   - CSRF formu yok (istek dışarıdan geliyor); güvenliği `retrieve` sorgusu sağlar.
7. **PayTR:** `httpx` ile `POST https://www.paytr.com/odeme/api/get-token`. `paytr_token`, alanların dokümandaki sırayla birleştirilmesi + `merchant_salt`, `merchant_key` ile HMAC-SHA256, base64.
   - `payment_amount` kuruş cinsinden (199,00 TL → `19900`); `user_basket` base64 JSON.
   - Bildirim ucu `POST /odeme/paytr/bildirim`: `verify_notification` → `apply_result` → `PlainTextResponse("OK")`. İmza yanlışsa 400.
   - Karşılaştırmayı `safe_equals` ile yap (`core/security.py`'da var).
   - **Not:** PayTR bildirimi internetten erişilen bir adrese gönderir; `localhost`'a gelmez. Fatih'in sunucusu kurulana kadar `FakeProvider` + birim testleriyle ilerle. PayTR `user_ip` alanında yerel IP'yi kabul etmeyebilir: test için gerçek dış IP'ni ver.
8. **CSP** (`app/main.py`):
   - `frame-src https://www.paytr.com` ekle.
   - `form-action`'a `https://sandbox-cpp.iyzipay.com` ekle (form POST'undan sonra yapılan 303 yönlendirmesi de bu kurala takılır).
   - `frame-ancestors 'none'` olduğu gibi kalsın.
9. **Ayarlar** (`config.py`): `payment_provider`, `payment_live`, `iyzico_api_key`, `iyzico_secret_key` (`repr=False`), `iyzico_base_url = "https://sandbox-api.iyzipay.com"`, `paytr_merchant_id`, `paytr_merchant_key`, `paytr_merchant_salt` (`repr=False`), `paytr_test_mode = 1`.
   - `build_provider(settings)` fabrikası (`build_notifier`'a bak).
   - Kilit kontrolü burada: `payment_live` kapalıyken canlı adres → `RuntimeError`.
10. **Pilot:** `scripts/make_pilot.py <slug>` atölyeyi `is_pilot=True` yapar. Pilotlar için ekran yok, komutu yalnızca Fatih çalıştırır.
11. **Ekran:** `GET /abonelik` (yalnız OWNER). Gösterilenler: paket, bitiş tarihi, "Öde" butonu (CSRF'li form), son 10 ödeme (`scoped(Payment, user)`).
12. **Mevcut `/webhooks/odeme`:** Dokunma; genel HMAC örneği olarak kalıyor. TODO yorumunu "PayTR bildirimi `/odeme/paytr/bildirim`'de" diye güncelle.
13. **Testler** (`tests/test_subscription.py`, `tests/test_payments.py`):
    - `extend`: süresi bitmiş → şimdiden; geçerli → bitiş tarihinden; 31 Ocak → Şubat sonu
    - Fake akış: başlat → `PENDING`; başarılı sonuç → `PAID`, bitiş tarihi +1 ay
    - Aynı sonuç ikinci kez → bitiş tarihi **değişmedi**
    - Tutar uyuşmazlığı → `FAILED`, abonelik aynı
    - PayTR yanlış `hash` → 400, `Payment` hâlâ `PENDING`; doğru `hash` → yanıt gövdesi tam olarak `OK`
    - iyzico: sahte SDK `paymentStatus="FAILURE"` döndürür → `FAILED`
    - `payment_live=False` + `paytr_test_mode=0` → uygulama açılmıyor
    - B atölyesi `/abonelik`'te A'nın ödemelerini görmüyor
    - Pilot atölyede "Öde" butonu yok
    - `repr(settings)` ve `caplog` içinde anahtarlar yok

### Dikkat
- İki sağlayıcı da test ortamında **test kartları** verir (sağlayıcıların geliştirici dokümanında). Gerçek kartla deneme yapma.
- `docs/KARARLAR.md`: canlıya geçiş ancak bir fatura yapısı kurulursa olur. `PAYMENT_LIVE=true`'yu kimse açmaz.

### Teslim
PR + iyzico test ödemesinin ekran kaydı (başlat → öde → bitiş tarihi uzadı) + test çıktısı.

---

## PROJE 2: Atölye ayarları ekranı (telefon) + pilot kurulumu
**Sahip:** Seher · **Eş:** Alper · **Trello:** `[Seher] H4 · Pilot atölyelerin vitrin ve hesap kurulumu`

### Kazanım
- Tenant'ın **kendi** kaydını düzenlemek: `Workshop` kiracı modelin kendisidir; `scoped()` yerine `db.get(Workshop, user.workshop_id)` kullanılır. URL'de atölye id'si **olmaz**.
- Girdiyi kaydetmeden önce normalleştirmek: kullanıcı `0532 111 22 33` yazar, DB'ye `+905321112233` girer.
- Mevcut bir yardımcıyı yeniden kullanmak (`normalize_phone`, Deha'nın kodu).

### Problem
Vitrindeki WhatsApp butonu `workshop.phone`'a bakıyor, ama atölyenin telefonunu girebileceği bir ekran yok. Pilot atölyeler kurulurken her birinin numarası girilmeli, yoksa vitrinde sipariş butonu çıkmaz.

### Gereksinimler
- `GET/POST /atolye/ayarlar`: yalnız **OWNER** (`require_owner`), formda CSRF
- Alanlar: atölye adı (2–120 karakter) ve telefon (boş bırakılabilir)
- Telefon `normalize_phone` ile doğrulanır; geçersizse form aynı sayfada hata mesajıyla döner, DB değişmez
- Boş telefon → `None` → vitrinde WhatsApp butonu kaybolur
- Vitrin linki (`/v/{slug}`) sayfada **salt okunur** gösterilir. Slug değişmez, değişirse paylaşılmış linkler kırılır.
- Üst menüde "Atölye ayarları" bağlantısı yalnız OWNER'a görünür
- Inline script/style yok; renkler `:root` değişkenlerinden

### Adım Adım Çözüm Algoritması
1. **Önce git:** `git switch main && git pull`, sonra `git switch -c seher/atolye-ayarlari`. Eski branch'lerinden **çalışma**. Her gün işe başlarken `git pull origin main`.
2. **Önce açık iş:** PR #3'ün ekran görüntüleri (telefon + masaüstü).
3. Pydantic şeması (`app/modules/workshop/schemas.py`):
   ```python
   class WorkshopSettingsIn(BaseModel):
       name: str = Field(min_length=2, max_length=120)
       phone: str | None = None

       @field_validator("phone")
       @classmethod
       def _phone(cls, v: str | None) -> str | None:
           v = (v or "").strip()
           return normalize_phone(v) if v else None
   ```
   `ValueError` Pydantic'te doğrulama hatasına döner. Örnek: `customers/router.py`'deki `CustomerIn`.
4. Router (`app/modules/workshop/router.py`): GET formu doldurur, POST doğrular ve kaydeder, sonra **303** ile `/atolye/ayarlar?kaydedildi=1`. Router'ı `app/main.py`'deki listeye ekle.
5. Şablon `app/templates/workshop/settings.html`: `base.html`'i genişletsin, `{{ csrf_token }}` gizli alanı olsun. Telefon alanı `type="tel"`, `inputmode="tel"`, `autocomplete="tel"`.
6. `base.html` menüsüne `{% if user and user.role == "OWNER" %}` ile bağlantı ekle.
7. **Testler** (`tests/test_workshop_settings.py`):
   - OWNER `0532 111 22 33` kaydeder → DB'de `+905321112233`
   - Geçersiz numara (`123`) → hata mesajı, DB değişmedi
   - Telefon boşaltılır → `None`, vitrinde `wa.me` yok
   - Telefon kaydedilince vitrinde `wa.me/905321112233` var
   - STAFF → 403 · CSRF token yok → 403
8. **Pilot kurulumu** (Fatih'in sunucusu hazır olunca, H4'ün ikinci yarısı):
   - 3 pilot atölyenin hesabını aç; atölye adı, telefon ve ürünleri gir.
   - Fatih'e slug'ları ver; `make_pilot.py` ile ücretsiz yapılacaklar.
   - Görseller Alper'in galerisi birleşince eklenir.
9. 1 sayfalık **Hızlı başlangıç** kılavuzu (PDF, ekran görüntülü): kayıt → atölye ayarları → ürün ekle → sipariş aç → takip linkini gönder.

### Teslim
PR + ayarlar ekranının telefon (375 px) ve masaüstü ekran görüntüsü + test çıktısı · kılavuz PDF karta ek.

---

## PROJE 3: Paket tanımları + fiyatlandırma sayfası
**Sahip:** Hayrettin · **Eş:** Çınar · **Trello:** `[Hayrettin] H4 · Fiyat paketleri + fiyatlandırma sayfası`

### Kazanım
- İş kuralını veriye çevirmek: paket = kod içinde değişmez bir `dataclass`
- Domain fonksiyonunu DB'siz test etmek
- Kararı **veriyle** vermek: H1 görüşmelerindeki "ayda ne öderdiniz?" cevapları

### Problem
Abonelik sayfası (Hasan) hangi paketin ne kadar olduğunu bilmeli. Herkese açık bir fiyatlandırma sayfası da paketleri göstermeli. Pilot dönemde herkes ücretsiz, ama demo günü "ürün satılırsa fiyatı ne?" sorusunun cevabı hazır olmalı.

### Gereksinimler
- `app/domain/plans.py` (yukarıdaki **ortak arayüz** imzası) + 2 ücretli paket + `PILOT`
- `can_create_order(plan, orders_this_month) -> bool` (saf fonksiyon; `None` = sınırsız)
- `GET /fiyatlar`: giriş gerektirmez, paketleri `PLANS`'tan çizer (şablonda sabit fiyat yok)
- Sayfada not: "Pilot programındaki atölyeler için demo gününe kadar ücretsiz"
- Fiyatlar `Decimal`, ekranda `1.234,00 ₺` biçiminde

### Adım Adım Çözüm Algoritması
1. **Öncelik sırası:**
   1. H2 ürün düzenleme ekranı
   2. H3 teklif PDF: PR #13'teki 6 adım. Yapay zekâ çıktısını olduğu gibi yükleme; her dosyayı mevcut `orders/service.py` ve `domain/pricing.py`'yi **bozmadan** yaz.
   3. Bu proje
2. Pazartesi ilk iş: `plans.py`'yi yukarıdaki imzayla **küçük bir PR** olarak aç. Hasan buna bağlı.
3. H1 görüşme notlarından cevapları bir tabloya dök (atölye, şu an ne kullanıyor, ayda ne öderdi). Ortalamaya göre 2 paket öner. Tabloyu karta ekle.
4. `can_create_order` + testleri (`tests/test_plans.py`): sınırın altı / eşit / üstü, `None` sınırsız, bilinmeyen kod → `ValueError`.
5. `/fiyatlar` sayfası: `app/templates/public/pricing.html`. Tasarımı Seher'in marka değişkenleriyle yap; vitrin sayfasındaki kart yapısını örnek al.
6. Paket sınırının sipariş oluşturmaya bağlanması **H5'te** (Çınar'la birlikte). Bu hafta yalnızca fonksiyon ve test.
7. Test: `/fiyatlar` giriş olmadan `200`; her paketin adı ve fiyatı sayfada var.

### Teslim
Paket tablosu karta ek + PR + test çıktısı.

---

## PROJE 4: Termin hesabı + gecikme uyarısı
**Sahip:** Çınar · **Eş:** Hayrettin · **Trello:** `[Çınar] H4 · Termin hesabı ve gecikme uyarısı`

### Kazanım
- Tarih aritmetiğini domain'e almak: iş günü, hafta sonu, resmî tatil
- Durumu **hesaplanan** değer olarak göstermek (DB'ye "gecikti" yazılmaz)

### Problem
Usta sipariş açarken termini kafadan yazıyor ve gecikmeyi panoda fark etmiyor. Ürünün ortalama üretim süresinden termin önerilmeli; terminine 2 gün kalan iş sarı, geçen iş kırmızı görünmeli.

### Gereksinimler
- `Product.avg_production_days: int | None` (migration). Ürün formundaki alanı Hayrettin'le konuşarak ekle.
- `app/domain/deadline.py`:
  - `add_business_days(start: date, days: int, holidays: frozenset[date]) -> date`
  - `deadline_state(due: date | None, today: date) -> "none" | "ok" | "soon" | "late"`
- Sipariş formunda termin önerisi: kalemlerdeki **en uzun** süre. Kullanıcı değiştirebilir.
- Panoda kartlar `.ticket--soon` ve `.ticket--late` sınıflarıyla işaretlenir; renk `:root`'tan gelir
- `DELIVERED` ve `CANCELLED` siparişler hiçbir zaman "late" değildir

### Adım Adım Çözüm Algoritması
1. **Önce:** PR #9 (çok kalemli siparişin backend'i ve testleri), sonra H3 pano. Trello'da "tamamlandı" işaretini iş bitince koy.
2. `deadline.py` + `tests/test_deadline.py` **önce**:
   - Cuma + 1 iş günü → Pazartesi
   - 28 Ekim 2026 Çarşamba + 1 iş günü → 30 Ekim Cuma (29 Ekim atlanır; tatil listesini `TR_HOLIDAYS_2026_2027` sabiti olarak domain'e yaz; dini bayram tarihleri her yıl değişir, kaynağını yorumda belirt)
   - Termin bugünden 2 gün sonra → `soon`; dün → `late`; `None` → `none`
3. Migration: `avg_production_days`. Son head'e bağla, dosyayı oku.
4. Termin önerisi: `GET /siparisler/termin-onerisi?urun=1&urun=3` HTMX parçası ya da form yüklenirken hesap. Sayfaya özel JS **`app.js`**'te (sipariş formu senin dosyan); `board.js`'e karıştırma.
5. Pano: şablonda `deadline_state(order.due_date, today)` sonucunu sınıfa çevir. `today`'i router'dan ver, şablonda `now()` çağırma (test edilemez).
6. **Stretch:** Her sabah "bugün terminli / geciken işler" özeti. Bunu bir `scripts/daily_digest.py` olarak yaz; Deha'nın `Notifier`'ını kullansın. Cron'a bağlama işi Fatih'in deploy'unda.
7. Testler: domain testleri + pano HTML'inde geciken siparişin kartında `ticket--late` var + B atölyesinin siparişi listede yok.

### Teslim
PR + panonun ekran görüntüsü (sarı ve kırmızı kart) + test çıktısı.

---

## PROJE 5: Lansman içerik planı
**Sahip:** Deha · **Eş:** Hasan · **Trello:** `[Deha] H4 · Lansman içerik planı (Instagram / LinkedIn)`

### Kazanım
- Ürünü teknik olmayan bir dille anlatmak: problem → çözüm → kanıt
- Kişisel veriye dikkat: müşteri adı, telefon, sipariş görseli izinsiz paylaşılmaz

### Problem
Demo gününe kadar ürünün görünür olması ve pilot atölyelerin hikâyesinin anlatılması gerekiyor. Ürün **ücretsiz pilot** aşamasında, satış yok; içerik buna göre yazılmalı.

### Gereksinimler
- 2 haftalık takvim, en az 8 paylaşım: problem, çözüm, pilot hikâyesi, demo videosu
- Hiçbir paylaşımda fiyat ya da "satın al" çağrısı yok; çağrı: "pilot programına katıl"
- İlk 3 içerik hazır (Alper'in fotoğraf ve videosuyla)
- Pilot atölyeden **yazılı** paylaşım izni; ekran görüntülerinde müşteri adı ve telefonu bulanık

### Adım Adım Çözüm Algoritması
1. **Önce:** H3 e-posta adaptörü + bildirim geçmişi, PR #5'in SMS ekran görüntüsü.
2. H1 araştırmandaki rakip hesaplarından 3 örnek seç: ne işe yarıyor, ne yaramıyor.
3. Takvimi tabloya dök: tarih, kanal, başlık, görsel, metin, sorumlu.
4. Demo ortamında (`scripts/seed_demo.py`) sahte verilerle ekran görüntüsü al; gerçek müşteri verisi kullanma.
5. İzin metnini Hasan'ın KVKK metniyle uyumlu yaz (1 paragraf yeter).

### Teslim
Takvim + ilk 3 içerik karta ek + Cuma demo.

---

## PROJE 6: Takip sayfasında "ürününüz yapılıyor" videosu
**Sahip:** Alper · **Eş:** Seher · **Trello:** `[Alper] H4 · Takip sayfasında "ürününüz yapılıyor" videosu`

### Kazanım
- Görselde kurduğun "dosya türünü içerikten anla" kuralını videoya genişletmek
- Büyük dosyayı akıllıca sunmak: `preload="none"`, `Range` isteği (206)
- Gizli/açık medya ayrımını müşteri tarafında test etmek

### Problem
Müşteri takip linkinde ürününün yapım aşamasından kısa bir video görmek istiyor. Video mobil veriyi boşa harcamamalı ve atölyenin gizli işaretlediği medya müşteriye görünmemeli.

### Gereksinimler
- MP4 kabul edilir: içerikte 4. byte'tan itibaren `ftyp` imzası (uzantıya bakılmaz)
- Ayrı boyut sınırı: `max_video_mb` (varsayılan 20), görsel sınırından bağımsız
- Takip sayfasında `<video controls preload="none" playsinline>`; otomatik oynatma yok
- `is_public=False` medya takip sayfasında yok ve doğrudan URL'si 404
- `Range: bytes=0-99` isteğine `206` (iPhone Safari bunu ister)

### Adım Adım Çözüm Algoritması
1. **Önce:** H3 galeri + `cover_url()` (Seher'in vitrini buna bağlı).
2. `media/service.py`'de `sniff_type(head: bytes)` fonksiyonuna MP4 dalını ekle; JPEG/PNG/WebP dalları bozulmasın.
3. Yüklemede boyut kontrolünü türe göre yap; büyük dosyayı belleğe tümüyle okumadan, parça parça yaz.
4. Video için küçük resim **yok** (ffmpeg kurmuyoruz). Şablonda video ikonu göster.
5. Sunum ucu `FileResponse`; `Range` desteğini testle doğrula.
6. **Testler** (`tests/test_media_video.py`):
   - Sahte MP4 başlığı (`b"\x00\x00\x00\x18ftypmp42" + ...`) kabul
   - `.mp4` uzantılı JPEG → kabul edilir ama türü `image/jpeg` (içerik kazanır); uzantısı `.mp4` olan rastgele byte → 400
   - Sınır üstü video → 413
   - Gizli video takip sayfasında yok, URL'si 404
   - `Range` isteği → 206

### Teslim
PR + telefonda takip sayfası ekran kaydı + test çıktısı.

---

## Fatih: sunucuya ilk deploy (öğrenciler izler)
**Trello:** `[Fatih] H4 · Sunucuya ilk deploy + yedek + harcama alarmı`

- VPS + alan adı + `docker compose up -d` (Caddy otomatik HTTPS)
- `.env` prod: `ENV=prod`, `COOKIE_SECURE=true`, güçlü `SECRET_KEY`, `PAYMENT_PROVIDER=iyzico`, `PAYMENT_LIVE=false`
- PayTR panelinde Bildirim URL: `https://<alan-adı>/odeme/paytr/bildirim`
- `scripts/backup.sh` cron'da + bir kez geri yükleme denemesi (checklist #20); harcama alarmı (#22)

---

## Herkes için hatırlatma (H3'ten öğrendiklerimiz)

| Ne oldu | Ders |
|---|---|
| Eski bir branch'ten PR açıldı; birleşse main'deki 877 satır silinecekti | Her işe `git switch main && git pull` ile başla, **yeni** branch aç. PR'ı açmadan önce GitHub'daki "Files changed" sekmesine bak: silmediğin dosyayı siliyor görünüyorsa dur. |
| Aynı iş GitHub web arayüzünden ikinci kez yüklendi | Web upload yok. `git add` → `git commit` → `git push` → PR. |
| Yapay zekânın ürettiği kod projeye uymadı, mevcut modülleri silecekti | Yapay zekâ kullanabilirsin, ama önce mevcut dosyayı ona **göster** ve çıktıyı satır satır oku. Anlamadığın satırı PR'a koyma. |
| Kart "tamamlandı" işaretlendi, iş bitmemişti | Tamamlandı = PR açık + testler yeşil. Önce PR. |
| Vitrinde kulüp logosu kullanıldı | Satılacak üründe başkasının markası ya da lisanslı görsel olmaz. |
