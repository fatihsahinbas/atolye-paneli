"""Bildirim gönderimi.  Sahip: Deha

Yeni kanal eklemek = Notifier protokolünü uygulayan bir sınıf yazmak (WhatsApp, SMS, e-posta).
Sipariş modülü kanalı bilmez; yalnızca notify_status_change() çağırır.
"""
import logging
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.domain.order_status import LABELS
from app.modules.notifications.models import Notification, NotificationStatus
from app.modules.orders.models import Order

log = logging.getLogger("atolye.notify")


class Notifier(Protocol):
    channel: str

    def send(self, recipient: str, message: str) -> None: ...


class ConsoleNotifier:
    """Geliştirme ortamı: mesajı log'a yazar (telefon maskelenir)."""

    channel = "console"

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []  # testler için

    def send(self, recipient: str, message: str) -> None:
        self.sent.append((recipient, message))
        log.info("Bildirim → %s: %s", recipient, message)


def build_message(order: Order, base_url: str) -> str:
    return (
        f"Merhaba {order.customer.first_name}, siparişinizin durumu: {LABELS[order.status]}. "
        f"Takip: {base_url.rstrip('/')}/t/{order.tracking_code}"
    )


def notify_status_change(db: Session, order: Order, notifier: Notifier, base_url: str) -> Notification:
    customer = order.customer
    n = Notification(
        workshop_id=order.workshop_id,
        order_id=order.id,
        channel=notifier.channel,
        recipient=customer.phone,
        message=build_message(order, base_url),
    )
    db.add(n)
    if not customer.contact_consent_at or not customer.phone:
        n.status = NotificationStatus.SKIPPED  # KVKK: rıza yoksa gönderme
    else:
        try:
            notifier.send(customer.phone, n.message)
            n.status, n.sent_at = NotificationStatus.SENT, utcnow()
        except Exception:  # kanal hatası siparişi bozmasın
            log.exception("Bildirim gönderilemedi (order=%s)", order.id)
            n.status = NotificationStatus.FAILED
    db.commit()
    return n
