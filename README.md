# ◆ Atölye Paneli

Kişiye özel üretim yapan küçük atölyeler (kuyumcu, filografi, el sanatı) için
**sipariş → üretim → teslim** takibi, müşteri takip linki ve vitrin sayfası. Çok kiracılı (multi-tenant) SaaS.

## Hızlı başlangıç

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # çıktıyı .env → SECRET_KEY
alembic upgrade head
python -m scripts.seed_demo                             # demo@atolye.local / demo-sifre-123
uvicorn --factory app.main:create_app --reload
```

http://localhost:8000 → giriş · http://localhost:8000/v/demo-atolye → vitrin

Testler: `pytest -q` · Lint: `ruff check .` · Paket denetimi: `pip-audit -r requirements.txt`

## Mimari

Modüler monolit. Her modül kendi `models.py / service.py / router.py` dosyalarına sahip.
`app/domain/` saf Python'dur (FastAPI/SQLAlchemy import etmez), tek başına test edilir.

```
app/
  core/        config, db, güvenlik, tenant izolasyonu, şablon, log maskeleme
  domain/      order_status.py (state machine) · pricing.py (fiyat motoru)
  modules/
    auth/          Hasan    kayıt, giriş, oturum, rol, hesap silme
    workshop/      Hasan    atölye (tenant)
    customers/     Deha     müşteri, KVKK rıza, anonimleştirme
    catalog/       Seher+Hayrettin  ürün, fiyat önizleme, altın fiyatı
    orders/        Çınar    sipariş, durum geçişi, kanban
    media/         Alper    güvenli görsel yükleme
    notifications/ Deha     bildirim outbox + kanal adaptörleri
    tracking/      Deha     /t/{kod} müşteri takip sayfası
    showcase/      Seher    /v/{slug} vitrin
    payments/      Hasan    imzalı ödeme webhook'u
  templates/ static/        Seher (UI/marka)
migrations/   Alembic
tests/        30 test: domain, auth, IDOR, upload, webhook
```

### Altın kuralları

1. Tenant tablosuna erişim **yalnızca** `scoped()` / `get_owned()` ile. Başka atölyenin kaydı → 404.
2. Sipariş durumu **yalnızca** `change_status()` → `ensure_transition()` ile değişir.
3. Para hesabı **Decimal**; float yasak. Sipariş anındaki fiyat dondurulur.
4. Durum değiştiren her form `csrf_token` taşır; HTMX istekleri başlıkla gönderir.
5. Şablonlarda `|safe` yasak; inline `<script>` / `style=` yasak (CSP `'self'`).
6. Yeni özellik = önce test (`tests/`), sonra kod. PR'sız `main`'e push yok.

## Güvenlik checklist durumu (iskelet, hafta 2)

```
✅ Tamam : 1 (.env, varsayılansız SECRET_KEY), 2 (.gitignore), 3-4 (rol + tenant izolasyonu, IDOR testi),
           5 (giriş/kayıt rate limit), 6 (Pydantic), 7 (magic-byte, boyut, uuid ad), 8 (CORS yok = tek origin),
           9 (CSP, nosniff, DENY, Referrer), 10 (Caddy HTTPS + HSTS), 11 (Argon2id), 12 (HttpOnly/Secure/Lax),
           13 (genel hata sayfası, prod'da /docs kapalı), 14 (log maskeleme), 15 (ORM, parametreli),
           16 (Jinja autoescape), 17 (HMAC + timestamp + idempotency), 18 (OWNER/STAFF), 21 (gerçek silme + anonimleştirme)
⚠️ Eksik : 19 (pip-audit CI'a eklenecek), 20 (backup.sh hazır, cron + restore testi yapılacak),
           22 (VPS/SMS/WhatsApp harcama alarmı), 23 (yayın öncesi saldırgan testi — hafta 5),
           5 (rate limit tek süreçte; çok worker'da Redis'e taşınmalı)
```

## Production

```bash
cp .env.example .env   # prod bölümünü doldur
docker compose up -d --build
```
Caddy otomatik sertifika alır. DB portu dışarı açılmaz. Yedek: `scripts/backup.sh` (gpg şifreli).
