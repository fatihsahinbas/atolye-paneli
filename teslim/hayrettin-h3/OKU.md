# Hayrettin · H3 Teklif PDF teslimi (13 Kas, Trello zip)

Zip'teki 4 dosya **olduğu gibi** bu klasöre kondu. Uygulamaya bağlı değiller.

Neden yerlerine konmadı:
- `pricing.py` → `app/domain/pricing.py`'nin yerine geçerse fiyat motoru (GOLD, GOLD_COST_PLUS, FIXED, PER_CM2) silinir.
- `service.py` → `app/modules/orders/service.py`'nin yerine geçerse `change_status()` ve sipariş akışı silinir.
- `router.py`: `get_current_workshop_id` projede yok; prefix `/orders` (projede `/siparisler`).
- `test_orders_tenancy.py`: `app.main.app`, `db_session`, `normal_user_token_headers` projede yok; mevcut aynı adlı test dosyasının üstüne yazardı.
- PDF için `reportlab` kullanılmış; ödevde `fpdf2` (requirements'ta yok).

Yapılacaklar: `docs/odevler/hafta-3.md` → PROJE 2'nin adımları. PR açıklamasında ayrıntılı liste var.
