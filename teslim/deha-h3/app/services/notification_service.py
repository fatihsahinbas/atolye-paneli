import logging
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.notifiers.multi import MultiNotifier

logger = logging.getLogger(__name__)


def notify_status_change(order, notifier: MultiNotifier, db: Session) -> Notification:
    """Sipariş durumu değişince kanal seçip gönderir, kaydı yazar."""
    message = f"Sayın {order.customer.name}, {order.id} numaralı siparişinizin durumu: {order.status}."
    channel, success = notifier.choose_and_send(order.customer, message)

    status = "SENT" if success else ("SKIPPED" if channel == "SKIPPED" else "FAILED")
    notif = Notification(order_id=order.id, channel=channel, status=status)
    db.add(notif)
    db.commit()
    db.refresh(notif)

    logger.info("notification order=%s channel=%s status=%s recipient=%s",
                order.id, channel, status,
                order.customer.phone or order.customer.email or "-")
    return notif


def retry_notification(notification_id: int, notifier: MultiNotifier, db: Session, workshop) -> Notification | None:
    """FAILED kaydı yeniden gönderir. SENT/SKIPPED idempotent (değişmez). 404 → None."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if notif is None:
        return None
    if notif.order.workshop_id != workshop.id:
        return None
    if notif.status != "FAILED":
        return notif  # idempotent: tekrar gönderme

    order = notif.order
    message = f"Sayın {order.customer.name}, {order.id} numaralı sipariş tekrar bildirimi: {order.status}."
    channel, success = notifier.choose_and_send(order.customer, message)

    notif.channel = channel
    notif.status = "SENT" if success else ("SKIPPED" if channel == "SKIPPED" else "FAILED")
    db.commit()
    db.refresh(notif)

    logger.info("retry notification=%s channel=%s status=%s", notif.id, notif.channel, notif.status)
    return notif