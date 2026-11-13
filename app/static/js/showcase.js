// Vitrin: ürün kartına tıklayınca detay modalını aç. Sahip: Seher
// Inline <script>/onclick yok (CSP 'self'); görünürlük CSS sınıfıyla (.modal.open).
document.addEventListener("DOMContentLoaded", () => {
  let lastCard = null;

  const open = (card) => {
    const modal = document.getElementById(card.dataset.modalId);
    if (!modal) return;
    lastCard = card;
    modal.classList.add("open");
    const close = modal.querySelector(".close");
    if (close) close.focus();
  };

  const closeAll = () => {
    document.querySelectorAll(".modal.open").forEach((m) => m.classList.remove("open"));
    if (lastCard) lastCard.focus();
  };

  document.querySelectorAll(".product-card[data-modal-id]").forEach((card) => {
    card.addEventListener("click", () => open(card));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open(card);
      }
    });
  });

  document.addEventListener("click", (e) => {
    // Çarpı butonu ya da modalın dışındaki karanlık alan
    if (e.target.closest(".close") || e.target.classList.contains("modal")) closeAll();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });
});
