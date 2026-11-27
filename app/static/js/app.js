document.addEventListener("DOMContentLoaded", () => {
    const items = document.getElementById("order-items");
    const total = document.getElementById("order-total");

    if (!items || !total || !window.htmx) return;

    const due = document.getElementById("due-date");
    const hint = document.getElementById("due-hint");
    let dueTouched = false;
    if (due) due.addEventListener("input", () => { dueTouched = true; if (hint) hint.hidden = true; });

    // Termin önerisi: kalemlerdeki en uzun üretim süresi (kullanıcı elle girdiyse dokunma)
    function refreshDue() {
        if (!due || dueTouched) return;
        const ids = [...items.querySelectorAll('select[name="product_id"]')].map((s) => s.value);
        const qs = ids.map((id) => "urun=" + encodeURIComponent(id)).join("&");
        fetch("/siparisler/termin-onerisi?" + qs, { credentials: "same-origin" })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (!data || dueTouched) return;
                due.value = data.due_date || "";
                if (hint) hint.hidden = !data.due_date;
            })
            .catch(() => {});
    }

    // Toplam fiyatı ve termin önerisini yeniden hesapla
    function refreshTotal() {
        htmx.trigger(total, "recalculate");
        refreshDue();
    }

    // Ürün veya adet değişince hesapla
    items.addEventListener("change", (event) => {
        if (
            event.target.matches('select[name="product_id"]') ||
            event.target.matches('input[name="quantity"]')
        ) {
            refreshTotal();
        }
    });

    items.addEventListener("input", (event) => {
        if (event.target.matches('input[name="quantity"]')) {
            refreshTotal();
        }
    });

    // Son kalemin silinmesini engelle
    items.addEventListener("click", (event) => {
        const button = event.target.closest(
            'button[hx-post="/siparisler/kalem/sil"]'
        );

        if (!button) return;

        const rows = items.querySelectorAll("[data-order-item]");

        if (rows.length <= 1) {
            event.preventDefault();
            event.stopPropagation();
            alert("Siparişte en az bir ürün bulunmalıdır.");
        }
    }, true);

    // HTMX işlemi tamamlandığında toplamı güncelle
    document.body.addEventListener("htmx:afterSettle", (event) => {
        const element = event.detail.elt;

        if (!element) return;

        if (
            element.matches?.('button[hx-get="/siparisler/kalem/yeni"]') ||
            element.matches?.('button[hx-post="/siparisler/kalem/sil"]')
        ) {
            refreshTotal();
        }
    });

    // İlk açılışta hesapla
    refreshTotal();
});
