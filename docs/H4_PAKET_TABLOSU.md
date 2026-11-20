# H4 · Paket ve Fiyatlandırma Tablosu (H1 Görüşme Verilerine Dayalı)

H1 kapsamında kuyumcu ve el emeği atölyeleriyle yapılan görüşmelerde öne çıkan aylık ödeme eşikleri ve sipariş hacimlerine göre 3 katmanlı paket yapısı ve pilot indirimi tanımlanmıştır.

| Paket | Kod | Aylık Liste Fiyatı | Pilot Fiyatı (%50 İndirim · İlk 3 Ay) | Aylık Sipariş Sınırı | Personel (Usta) Sınırı | Hedef Segment (H1 Bulgusu) |
|---|---|---:|---:|---|---|---|
| **Başlangıç** | `baslangic` | 0 ₺ (Ücretsiz) | 0 ₺ | 20 sipariş / ay | 1 kullanıcı (Sahip) | Yeni başlayan, ayda 10–20 özel sipariş alan küçük el sanatı atölyeleri |
| **Atölye** *(Önerilen)* | `atolye` | 950 ₺ / ay | **475 ₺ / ay** | 150 sipariş / ay | 5 kullanıcı | Düzenli müşteri akışı olan kuyumcu ve orta ölçekli üretim atölyeleri |
| **Usta Pro** | `usta_pro` | 1.950 ₺ / ay | **975 ₺ / ay** | Sınırsız | Sınırsız | Çok ustalıklı, yüksek hacimli imalathane ve toptan/perakende çalışan atölyeler |

## Teknik Bağlantı Noktaları
- **Domain Kuralı (`app/domain/plans.py`):** `PLANS`, `get_plan()`, `effective_monthly_price()`, `remaining_orders()`, `can_create_order()` (Hasan'ın abonelik/ödeme modülüyle doğrudan uyumlu).
- **Herkese Açık Sayfa:** `GET /fiyatlar` (`app/templates/public/pricing.html`) — giriş gerektirmeden paketleri, aylık sipariş limitlerini ve pilot indirimini gösterir.
- **Testler (`tests/test_plans.py`):** Paket yapısı, %50 pilot indirimi hesabı, aylık sipariş limitleri ve `/fiyatlar` sayfası HTTP 200 testleri eklendi.
