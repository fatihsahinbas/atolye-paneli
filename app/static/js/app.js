// Sipariş formu: ürün veya adet değişince fiyat önizlemesini sunucudan çek.
// Inline <script> yok — CSP 'self' ile uyumlu.
document.addEventListener("DOMContentLoaded", () => {
  const product = document.getElementById("product");
  const qty = document.querySelector('input[name="quantity"]');
  if (!product || !qty || !window.htmx) return;

  const refresh = () => {
    const id = encodeURIComponent(product.value);
    const adet = encodeURIComponent(qty.value || "1");
    htmx.ajax("GET", `/urunler/${id}/fiyat?adet=${adet}`, { target: "#price", swap: "innerHTML" });
  };
  product.addEventListener("change", refresh);
  qty.addEventListener("input", refresh);
  refresh();
});

// --- VİTRİN MODAL (DETAY PENCERESİ) KODLARI ---
function openModal(id) {
  document.getElementById(id).style.display = "flex";
}

function closeModal(id) {
  document.getElementById(id).style.display = "none";
}

window.onclick = function(event) {
  if (event.target.classList.contains('modal')) {
    event.target.style.display = "none";
  }
}