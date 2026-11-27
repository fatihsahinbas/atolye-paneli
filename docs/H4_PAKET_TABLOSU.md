# H4 · Paket ve Fiyatlandırma Tablosu (H1 Görüşme Verilerine Dayalı)

H1 kapsamında kuyumcu ve el emeği atölyeleriyle yapılan görüşmelerde öne çıkan aylık ödeme eşikleri ve sipariş hacimlerine göre 3 katmanlı paket yapısı tanımlanmıştır. Pilot atölyeler demo gününe kadar ücretsizdir (`PILOT` paketi, `Workshop.is_pilot`; KARARLAR.md 13 Kasım).

| Paket | Kod | Aylık Liste Fiyatı | Aylık Sipariş Sınırı | Personel (Usta) Sınırı | Hedef Segment (H1 Bulgusu) |
|---|---|---:|---|---|---|
| **Başlangıç** | `BASLANGIC` | 0 ₺ (Ücretsiz) | 20 sipariş / ay | 1 kullanıcı (Sahip) | Yeni başlayan, ayda 10–20 özel sipariş alan küçük el sanatı atölyeleri |
| **Atölye** *(Önerilen)* | `ATOLYE` | 950 ₺ / ay | 150 sipariş / ay | 5 kullanıcı | Düzenli müşteri akışı olan kuyumcu ve orta ölçekli üretim atölyeleri |
| **Usta Pro** | `USTA_PRO` | 1.950 ₺ / ay | Sınırsız | Sınırsız | Çok ustalıklı, yüksek hacimli imalathane ve toptan/perakende çalışan atölyeler |

## Teknik Bağlantı Noktaları
- **Domain Kuralı (`app/domain/plans.py`):** `PLANS`, `get_plan()` (bilinmeyen kod → `ValueError`), `public_plans()`, `paid_plans()`, `can_create_order()`, `remaining_orders()`; fiyatlar `Decimal` (Hasan'ın abonelik/ödeme modülüyle doğrudan uyumlu).
- **Herkese Açık Sayfa:** `GET /fiyatlar` (`app/templates/public/pricing.html`) — giriş gerektirmeden paketleri, aylık sipariş limitlerini ve pilot notunu gösterir.
- **Testler (`tests/test_plans.py`):** Paket yapısı, aylık sipariş limitleri ve `/fiyatlar` sayfası HTTP 200 testleri eklendi.
