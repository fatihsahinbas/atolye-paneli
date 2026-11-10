// Ürün kartlarına tıklama olayını JS ile dinle (CSP uyumlu)
document.addEventListener("DOMContentLoaded", function() {
  const cards = document.querySelectorAll('.product-card');
  cards.forEach(card => {
    card.addEventListener('click', function() {
      const modalId = this.getAttribute('data-modal-id');
      if (modalId) {
        document.getElementById(modalId).style.display = "flex";
      }
    });
  });
});

// Modal (Detay Penceresi) Kapatma İşlemleri
document.addEventListener("click", function(event) {
  // Çarpı (X) butonuna basıldıysa
  if (event.target.classList.contains('close')) {
    event.target.closest('.modal').style.display = "none";
  }
  // Modalın dışındaki karanlık alana tıklandıysa
  if (event.target.classList.contains('modal')) {
    event.target.style.display = "none";
  }
});