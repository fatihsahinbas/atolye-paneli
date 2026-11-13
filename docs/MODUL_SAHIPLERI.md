# Modül sahipleri ve ilk görevler

Her öğrenci kendi modülünün sahibidir: kodu yazar, testini yazar, derste 5 dakika demosunu yapar.
Fatih: mimari, code review, deploy.

| Kişi | Modül | Hafta 1 (keşif) | Hafta 2-3 (inşa) | Hafta 4-5 (canlı) |
|---|---|---|---|---|
| **Seher** | UI/marka, vitrin, katalog görseli | 5 atölye sahibiyle görüşme; rakip vitrin incelemesi | Marka renkleri, logo, vitrinde ürün görseli, mobil uyum | Pilot atölye vitrinleri; **stretch:** fotoğraftan filografi önizleme |
| **Hayrettin** | Fiyat motoru, teklif, satış | 5 kuyumcuyla görüşme: işçilik nasıl hesaplanıyor? | Teklif/proforma PDF, ürün düzenleme, çok kalemli fiyat | Fiyat paketleri, satış sunumu, ilk 3 pilot imzası |
| **Hasan** | Auth, roller, KVKK, ödeme | KVKK aydınlatma metni + açık rıza metni taslağı | Personel ekleme (STAFF), şifre sıfırlama, aydınlatma sayfası | iyzico/PayTR abonelik, webhook → abonelik uzatma |
| **Çınar** | Sipariş akışı, kanban, termin | Atölyede bir siparişin gerçek yolculuğunu çiz | Çok kalemli sipariş, sürükle-bırak kanban (HTMX), gecikme uyarısı | Termin hesabı, üretim süresi raporu |
| **Deha** | Bildirim, takip linki, müşteri | WhatsApp Business API / SMS sağlayıcı araştırması | WhatsApp adaptörü (`Notifier`), e-posta adaptörü | Lansman içerikleri; **stretch:** canlı yayında satış |
| **Alper** | Medya, video | Rakiplerin ürün fotoğraf/video akışı | Thumbnail üretimi, galeri, ürün görseli | Tanıtım filmi, takip sayfasında "ürününüz yapılıyor" videosu |

## Haftalık ritim
- **Derste:** her modül 5 dk demo + Fatih code review
- **Ödev:** her öğrenci haftada en az 1 PR + testleri
- **Kural:** `pytest -q` yeşil değilse PR birleşmez

## Ödev formatı (PROJE N)
Her haftanın ödevleri "PROJE N" formatında yazılır: **Kazanım** + **Adım Adım Çözüm Algoritması**.

| Hafta | Ödev dosyası |
|---|---|
| H2 (9–13 Kasım) | [docs/odevler/hafta-2.md](odevler/hafta-2.md) |
| H3 (16–20 Kasım) | [docs/odevler/hafta-3.md](odevler/hafta-3.md) |
| H4 (23–27 Kasım) | [docs/odevler/hafta-4.md](odevler/hafta-4.md) |

Kararlar ve gerekçeleri: [docs/KARARLAR.md](KARARLAR.md)
