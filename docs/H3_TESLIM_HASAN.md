# H3 · E-posta ile süreli token kullanarak şifre sıfırlama

**Geliştirici:** Hasan

## Tamamlananlar
- `/sifremi-unuttum`: e-posta üzerinden sıfırlama talebi.
- `/sifre-yenile?token=...`: yeni şifre belirleme sayfası.
- 30 dakika geçerli, kriptografik rastgele, tek kullanımlık token.
- Veritabanında ham token yerine SHA-256 özeti saklama.
- Süresi dolan/kullanılan/eski token'ın reddi.
- Şifre güncellenince tüm eski oturumları geçersiz kılma.
- Hesap var/yok bilgisini açıklamayan genel geri bildirim.
- İstek sayısı sınırlaması, herkese açık formlarda CSRF kontrolü.
- SMTP ile gerçek e-posta gönderimi (ayarlanmış sunucuda).
- Alembic migrasyonu ve otomatik testler.

## Çalıştırma
1. `.env.example` dosyasından `.env` oluşturup `SECRET_KEY` tanımlayın.
2. Gerçek e-posta göndermek için `.env` içinde `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_STARTTLS` değerlerini ayarlayın. SMTP tanımlı değilse gerçek e-posta gönderilemez. Geliştirici ortamında şifre sıfırlama bağlantıları konsola dökülmez.
3. Bağımlılıkları yükleyin: `pip install -r requirements.txt -r requirements-dev.txt`.
4. Mevcut veritabanında `alembic upgrade head` çalıştırın.
5. Sunucuyu başlatın: `uvicorn app.main:create_app --factory --reload`.
6. Test: `python -m pytest -q`.

## Dosyalar
`app/modules/auth/password_reset.py`, `app/modules/auth/reset_email.py`, `app/modules/auth/router.py`, `app/modules/auth/models.py`, iki yeni şablon, `app/core/config.py`, `app/main.py`, `app/models.py`, Alembic sürümü, `tests/test_password_reset.py`.

**Test sonucu (13.11.2026):** 33 test geçti.

**Not:** Bu paket GitHub'a otomatik push edilmedi. Kullanıcının kendi dalına commit/push etmesi gerekiyor. H2 personel yönetimi ve KVKK kapsamı H3'ten ayrıdır.
