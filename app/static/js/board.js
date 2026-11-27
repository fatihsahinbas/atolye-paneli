// Üretim panosu: sürükle-bırak ile durum değiştirme.  Sahip: Çınar (H3)
// Karar sunucuda: POST /siparisler/{id}/tasi → 200 {ok:true} ya da 409 {ok:false, message}.
// Geçersizse kart eski yerine döner. Inline script yok (CSP 'self').
(() => {
  "use strict";

  const board = document.getElementById("orders-board");
  const message = document.getElementById("board-message");
  if (!board) return;

  let drag = null; // { card, parent, next, status } — yalnız sürükleme süresince

  function showMessage(text, isError = true) {
    if (!message) return;
    message.textContent = text;
    message.hidden = false;
    message.classList.toggle("alert-error", isError);
    window.setTimeout(() => { message.hidden = true; }, 4000);
  }

  function updateCounts() {
    board.querySelectorAll("[data-drop-zone]").forEach((column) => {
      const count = column.querySelectorAll(".ticket").length;
      const counter = column.querySelector(".count");
      if (counter) counter.textContent = count;
      const list = column.querySelector(".ticket-list");
      if (!list) return;
      let empty = list.querySelector(".empty");
      if (count === 0 && !empty) {
        empty = document.createElement("p");
        empty.className = "empty";
        empty.textContent = "—";
        list.appendChild(empty);
      } else if (count > 0 && empty) {
        empty.remove();
      }
    });
  }

  // Her taşıma kendi durumunu taşır: aynı anda iki istek birbirinin kartını geri koymaz.
  function restore(move) {
    if (move.next && move.next.parentNode === move.parent) {
      move.parent.insertBefore(move.card, move.next);
    } else {
      move.parent.appendChild(move.card);
    }
    move.card.dataset.currentStatus = move.status;
    updateCounts();
  }

  function csrfHeaders() {
    try {
      return JSON.parse(document.body.getAttribute("hx-headers") || "{}");
    } catch {
      return null;
    }
  }

  function submitMove(move, newStatus) {
    const headers = csrfHeaders();
    if (headers === null) {
      restore(move);
      showMessage("CSRF başlığı okunamadı.");
      return;
    }
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    headers["Accept"] = "application/json";

    move.card.classList.add("ticket-pending");
    fetch(`/siparisler/${move.card.dataset.orderId}/tasi`, {
      method: "POST",
      headers,
      body: new URLSearchParams({ to_status: newStatus }).toString(),
      credentials: "same-origin",
      redirect: "error", // oturum düşerse yönlendirme başarı sayılmasın
    })
      .then(async (response) => {
        const data = await response.json().catch(() => null);
        if (response.ok && data && data.ok === true) {
          move.card.dataset.currentStatus = newStatus;
          if (newStatus === "DELIVERED") {
            move.card.classList.remove("ticket--late", "ticket--soon");
          }
          showMessage("Sipariş durumu güncellendi.", false);
          return;
        }
        restore(move);
        showMessage((data && data.message) || "Sipariş durumu değiştirilemedi.");
      })
      .catch(() => {
        restore(move);
        showMessage("Sunucuya ulaşılamadı. Sayfayı yenileyip tekrar deneyin.");
      })
      .finally(() => {
        move.card.classList.remove("ticket-pending");
        updateCounts();
      });
  }

  board.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".ticket");
    if (!card || card.classList.contains("ticket-pending")) {
      event.preventDefault();
      return;
    }
    drag = { card, parent: card.parentNode, next: card.nextSibling, status: card.dataset.currentStatus };
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", card.dataset.orderId);
    card.classList.add("ticket-dragging");
  });

  board.addEventListener("dragend", () => {
    if (drag) drag.card.classList.remove("ticket-dragging");
    board.querySelectorAll(".col").forEach((c) => c.classList.remove("drop-active"));
    drag = null; // tıklama engeli bırakılmaz: sonraki tıklama detay sayfasını açar
  });

  board.addEventListener("dragover", (event) => {
    const column = event.target.closest("[data-drop-zone]");
    if (!column || !drag) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    column.classList.add("drop-active");
  });

  board.addEventListener("dragleave", (event) => {
    const column = event.target.closest("[data-drop-zone]");
    if (column && !column.contains(event.relatedTarget)) column.classList.remove("drop-active");
  });

  board.addEventListener("drop", (event) => {
    const column = event.target.closest("[data-drop-zone]");
    if (!column || !drag) return;
    event.preventDefault();
    column.classList.remove("drop-active");
    const newStatus = column.dataset.status;
    const list = column.querySelector(".ticket-list");
    if (!newStatus || newStatus === drag.status || !list) return;
    const move = drag;
    list.appendChild(move.card);
    updateCounts();
    submitMove(move, newStatus);
  });
})();
