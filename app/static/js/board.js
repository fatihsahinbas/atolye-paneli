
(() => {
  "use strict";

  const board = document.getElementById("orders-board");
  const message = document.getElementById("board-message");

  if (!board) return;

  let draggedCard = null;
  let originalParent = null;
  let originalNextSibling = null;
  let originalStatus = null;
  let originalCount = null;

  function showMessage(text, isError = true) {
    if (!message) return;

    message.textContent = text;
    message.hidden = false;
    message.classList.toggle("alert-error", isError);

    window.setTimeout(() => {
      message.hidden = true;
    }, 4000);
  }

  function updateCounts() {
    board.querySelectorAll("[data-drop-zone]").forEach((column) => {
      const count = column.querySelectorAll(".ticket").length;
      const counter = column.querySelector(".count");

      if (counter) {
        counter.textContent = count;
      }

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

  function restoreCard() {
    if (!draggedCard || !originalParent) return;

    if (
      originalNextSibling &&
      originalNextSibling.parentNode === originalParent
    ) {
      originalParent.insertBefore(draggedCard, originalNextSibling);
    } else {
      originalParent.appendChild(draggedCard);
    }

    draggedCard.dataset.currentStatus = originalStatus;
    updateCounts();
  }

  function submitStatus(card, newStatus) {
    const orderId = card.dataset.orderId;

    const body = new URLSearchParams();
    body.set("to_status", newStatus);
    body.set("note", "");

    card.classList.add("ticket-pending");

    const headers = {
      "HX-Request": "true",
      "Content-Type": "application/x-www-form-urlencoded",
      "Accept": "text/plain"
    };

    const csrfHeaders = document.body.getAttribute("hx-headers");

    if (csrfHeaders) {
      try {
        Object.assign(headers, JSON.parse(csrfHeaders));
      } catch {
        restoreCard();
        card.classList.remove("ticket-pending");
        showMessage("CSRF başlığı okunamadı.");
        return;
      }
    }

    fetch(`/siparisler/${orderId}/durum`, {
      method: "POST",
      headers,
      body: body.toString(),
      credentials: "same-origin"
    })
      .then(async (response) => {
        if (response.status === 204) {
          card.dataset.currentStatus = newStatus;
          showMessage("Sipariş durumu güncellendi.", false);
          return;
        }

        const errorText = await response.text();

        restoreCard();

        showMessage(
          errorText || "Sipariş durumu değiştirilemedi."
        );
      })
      .catch(() => {
        restoreCard();
        showMessage("Sunucuya ulaşılamadı. Tekrar deneyin.");
      })
      .finally(() => {
        card.classList.remove("ticket-pending");
        draggedCard = null;
        originalParent = null;
        originalNextSibling = null;
        originalStatus = null;
        updateCounts();
      });
  }

  board.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".ticket");

    if (!card) return;

    draggedCard = card;
    originalParent = card.parentNode;
    originalNextSibling = card.nextSibling;
    originalStatus = card.dataset.currentStatus;

    originalCount = originalParent
      .closest("[data-drop-zone]")
      ?.querySelector(".count")?.textContent;

    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", card.dataset.orderId);

    card.classList.add("ticket-dragging");
  });

  board.addEventListener("dragend", () => {
    if (draggedCard) {
      draggedCard.classList.remove("ticket-dragging");
    }

    board.querySelectorAll(".col").forEach((column) => {
      column.classList.remove("drop-active");
    });
  });

  board.addEventListener("dragover", (event) => {
    const column = event.target.closest("[data-drop-zone]");

    if (!column || !draggedCard) return;

    event.preventDefault();
    event.dataTransfer.dropEffect = "move";

    column.classList.add("drop-active");
  });

  board.addEventListener("dragleave", (event) => {
    const column = event.target.closest("[data-drop-zone]");

    if (
      column &&
      !column.contains(event.relatedTarget)
    ) {
      column.classList.remove("drop-active");
    }
  });

  board.addEventListener("drop", (event) => {
    const column = event.target.closest("[data-drop-zone]");

    if (!column || !draggedCard) return;

    event.preventDefault();
    column.classList.remove("drop-active");

    const newStatus = column.dataset.status;

    if (!newStatus || newStatus === originalStatus) {
      return;
    }

    const card = draggedCard;
    const list = column.querySelector(".ticket-list");

    if (!list) return;

    list.appendChild(card);
    updateCounts();

    submitStatus(card, newStatus);
  });

  board.addEventListener("click", (event) => {
    const card = event.target.closest(".ticket");

    if (card && card.dataset.suppressClick === "true") {
      event.preventDefault();
      card.dataset.suppressClick = "false";
    }
  });

  board.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".ticket");

    if (card) {
      card.dataset.suppressClick = "true";
    }
  });
})();
