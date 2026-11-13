# Proje kararları

Önemli kararlar burada tek satırlık gerekçeleriyle tutulur. Yeni karar en üste eklenir.
Bir kararı değiştirmek için yeni bir satır yazılır; eskisi silinmez, "değişti" diye işaretlenir.

| Tarih | Karar | Gerekçe | Etkisi |
|---|---|---|---|
| 13 Kasım 2026 | **Ödeme iki sağlayıcıyı destekler: iyzico ve PayTR.** | Sağlayıcı ilerde değişebilir; `Notifier`'daki protokol deseni ödemede de uygulanır. | `PaymentProvider` protokolü + `FakeProvider` / `IyzicoProvider` / `PaytrProvider`. Seçim `.env`'de `PAYMENT_PROVIDER`. `PAYMENT_LIVE=false` iken canlı adresle uygulama açılmaz. |
| 13 Kasım 2026 | **Atölye telefonu giriş ekranı (`/atolye/ayarlar`) Seher'de.** | Vitrindeki WhatsApp butonu `workshop.phone`'a bağlı, ama numarayı girecek ekran yoktu. | H4 PROJE 2. Telefon `normalize_phone` ile E.164 kaydedilir. |
| 13 Kasım 2026 | **Ürün adı "Atölye Paneli" olarak kalıyor.** | İsim oylaması yapılmadı; mevcut ad kodda, Trello'da ve sunumda zaten var. | Yeniden adlandırma işi yok. `Settings.app_name` tek yerden değiştirilebilir durumda kalır. |
| 13 Kasım 2026 | **Fatura kesen bir yapı (şahıs/limited) kurulmuyor; ürün ders projesi olarak ilerliyor.** | Eğitmenin iş sözleşmesindeki yan iş maddesi. | H4 abonelik ödemesi iyzico/PayTR **test (sandbox)** ortamında yapılır. Gerçek tahsilat yok. |
| 13 Kasım 2026 | **Demo günü hedefi güncellendi.** | Gerçek ödeme alınmayacak. | "Ödeme yapmış atölye" yerine: pilot atölyelerin gerçek siparişle kullanımı + uçtan uca **test ödemesi** (abonelik başlat → webhook → abonelik uzat). |
| 13 Kasım 2026 | **Pilot atölyeler ücretsiz deneme kullanıcısıdır.** | Fatura kesilemediği için ücret alınamaz. | H5 "pilot sözleşmesi" bir deneme/geri bildirim mutabakatıdır; ücret maddesi içermez. KVKK veri işleme maddesi yine gerekir. |
| 13 Kasım 2026 | **H1 araştırma kartları kapatıldı.** | Son tarih (9 Kasım) geçti; ilerlemek öncelikli. | Eksik araştırmalar ilgili H3 kartlarına not olarak düşüldü. |
| 13 Kasım 2026 | **Sayfaya özel JavaScript ayrı dosyada.** | `app.js`'in üzerine yazılması sipariş formunu bozdu (PR #6). | `app.js` sipariş formu · `showcase.js` vitrin · `board.js` pano. |
| 8 Kasım 2026 | **`main` korumalı (ruleset `Atolye-panel`).** | Kırık kodun ana dala girmesini önlemek. | PR + `ci` yeşil + branch güncel + eşin 1 onayı. Admin yalnızca PR'da bypass eder. |
| 8 Kasım 2026 | **Öğrenci PR'larını Claude açar ama birleştirmez.** | Eş review alışkanlığı. | Birleştirme: eş onayından sonra Fatih. |
| 6 Kasım 2026 | **Trello'ya yüklenen dosyalar Claude tarafından PR'a aktarılır.** | Git'e henüz alışmamış öğrencilerin teslimi kaybolmasın. | Hedef: herkes kendi `git push` + PR'ına geçsin. |

## İleride (ticarileşme olursa)
- İK'dan yazılı izin alınırsa ilk seçenek **Ruul** (şirketsiz fatura, abonelik desteği, %5 komisyon). Önce kullanım koşullarının SaaS aboneliğine uygunluğu kontrol edilir.
- Alternatif: şahıs işletmesi (4A sigortalı için Bağ-Kur doğmaz) → gelir oturunca limited.
