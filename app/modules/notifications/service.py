"""Bildirim gönderimi.  Sahip: Deha

Yeni kanal eklemek = Notifier protokolünü uygulayan bir sınıf yazmak (WhatsApp, SMS, e-posta).
Kanal seçimi: müşterinin telefonu varsa telefon kanalı (NOTIFY_CHANNEL), yoksa e-posta, ikisi de yoksa SKIPPED.
Sipariş modülü kanalı bilmez; yalnızca notify_status_change() çağırır.
Hangi kanalın kullanılacağına build_notifier() karar verir (NOTIFY_CHANNEL); main.py somut sınıfı bilmez.
"""
import logging
import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage
from typing import Protocol

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
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


class ConsoleEmailNotifier(ConsoleNotifier):
    """SMTP ayarı yokken e-posta kanalı: log'a yazar (adres maskelenir)."""

    channel = "email"


class EmailNotifier:
    """SMTP ile e-posta. Test için smtp_factory dışarıdan verilir."""

    channel = "email"

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        starttls: bool = True,
        subject: str = "Sipariş durumu",
        smtp_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        if not host or not sender:
            raise ValueError("email: SMTP_HOST ve SMTP_FROM zorunludur")
        self._host, self._port, self._user, self._password = host, port, user, password
        self._sender, self._starttls, self._subject = sender, starttls, subject
        self._factory = smtp_factory

    def __repr__(self) -> str:
        return f"EmailNotifier(host={self._host!r}, user={self._user!r}, password='***')"

    def send(self, recipient: str, message: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = self._subject
        msg["From"] = self._sender
        msg["To"] = recipient
        msg.set_content(message)
        with self._factory(self._host, self._port, timeout=10) as smtp:
            if self._starttls:
                smtp.starttls(context=ssl.create_default_context())  # sertifika doğrulanır
            if self._user:
                smtp.login(self._user, self._password)
            smtp.send_message(msg)


# --- HTTP tabanlı adaptörler (SMS / WhatsApp) ------------------------------


def normalize_phone(raw: str) -> str:
    """Türk telefon numarasını E.164 biçimine çevirir.

    0532 111 22 33 / +90 532 111 22 33 / 905321112233 / 532 111 22 33 → +905321112233
    Geçersiz numarada ValueError (notify_status_change bunu FAILED olarak yazar).
    """
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("0"):
        digits = digits[1:]
    if not digits.startswith("90"):
        digits = "90" + digits
    if len(digits) != 12:
        raise ValueError("Geçersiz telefon numarası")  # numara mesaja yazılmaz (KVKK)
    return "+" + digits


class _HttpNotifierBase:
    """Ortak HTTP davranışı. `channel` ve `_build_body` alt sınıflarda tanımlanır."""

    channel: str = ""

    def __init__(self, api_url: str, api_key: str, client: httpx.Client | None = None) -> None:
        if not api_url or not api_key:
            raise ValueError(f"{self.channel}: api_url ve api_key zorunludur")
        self._api_url = api_url
        self._api_key = api_key
        # Test için client dışarıdan verilebilir (httpx.MockTransport).
        self._client = client or httpx.Client(timeout=5.0)

    def __repr__(self) -> str:  # anahtar repr/str üzerinden görünmesin
        return f"{type(self).__name__}(api_url={self._api_url!r}, api_key='***')"

    def _build_body(self, phone_e164: str, message: str) -> dict:
        raise NotImplementedError

    def _build_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def send(self, recipient: str, message: str) -> None:
        phone = normalize_phone(recipient)
        response = self._client.post(
            self._api_url, json=self._build_body(phone, message), headers=self._build_headers(), timeout=5
        )
        if not response.is_success:
            # Anahtar burada yok; yalnızca durum kodu.
            raise RuntimeError(f"{self.channel} sağlayıcı hatası: status={response.status_code}")


class SmsNotifier(_HttpNotifierBase):
    channel = "sms"

    def _build_body(self, phone_e164: str, message: str) -> dict:
        return {"to": phone_e164, "message": message}


class WhatsAppNotifier(_HttpNotifierBase):
    channel = "whatsapp"

    def _build_body(self, phone_e164: str, message: str) -> dict:
        # Meta Cloud API biçimi; sağlayıcıya göre güncellenebilir.
        return {
            "messaging_product": "whatsapp",
            "to": phone_e164.lstrip("+"),
            "type": "text",
            "text": {"body": message},
        }


def build_notifier(settings: Settings) -> Notifier:
    """Ayarlara göre somut notifier döner. Bilinmeyen kanal / eksik anahtar → uygulama açılmaz."""
    channel = (settings.notify_channel or "console").lower()
    if channel == "console":
        return ConsoleNotifier()
    if channel == "sms":
        return SmsNotifier(api_url=settings.sms_api_url, api_key=settings.sms_api_key)
    if channel == "whatsapp":
        return WhatsAppNotifier(api_url=settings.whatsapp_api_url, api_key=settings.whatsapp_api_key)
    raise ValueError(f"Bilinmeyen NOTIFY_CHANNEL: {channel!r}")


def build_email_notifier(settings: Settings) -> Notifier:
    """SMTP ayarlıysa gerçek e-posta, değilse log'a yazan e-posta kanalı."""
    if settings.smtp_host and settings.smtp_from:
        return EmailNotifier(
            settings.smtp_host, settings.smtp_port, settings.smtp_user, settings.smtp_password,
            settings.smtp_from, settings.smtp_starttls, subject=f"{settings.app_name} · Sipariş durumu",
        )
    return ConsoleEmailNotifier()


# --- İş akışı ----------------------------------------------------------------


def build_message(order: Order, base_url: str) -> str:
    return (
        f"Merhaba {order.customer.first_name}, siparişinizin durumu: {LABELS[order.status]}. "
        f"Takip: {base_url.rstrip('/')}/t/{order.tracking_code}"
    )


def _send(n: Notification, notifier: Notifier, order_id: int | None) -> None:
    try:
        notifier.send(n.recipient, n.message)
        n.status, n.sent_at = NotificationStatus.SENT, utcnow()
    except Exception as exc:  # kanal hatası siparişi bozmasın
        # Hata mesajı log'a basılmaz (URL/anahtar/adres sızmasın); yalnızca tip + kanal. Detay DEBUG'da.
        log.warning("Bildirim gönderilemedi (order=%s kanal=%s hata=%s)", order_id, n.channel, type(exc).__name__)
        log.debug("Bildirim hata detayı", exc_info=True)
        n.status = NotificationStatus.FAILED


def notify_status_change(
    db: Session, order: Order, notifier: Notifier, base_url: str, email_notifier: Notifier | None = None
) -> Notification:
    """Telefon varsa telefon kanalı, yoksa e-posta, ikisi de yoksa ya da rıza yoksa SKIPPED."""
    customer = order.customer
    use_email = not customer.phone and bool(customer.email) and email_notifier is not None
    chosen = email_notifier if use_email else notifier
    n = Notification(
        workshop_id=order.workshop_id,
        order_id=order.id,
        channel=chosen.channel,
        recipient=customer.email if use_email else customer.phone,
        message=build_message(order, base_url),
    )
    db.add(n)
    if not customer.contact_consent_at or not n.recipient:
        n.status = NotificationStatus.SKIPPED  # KVKK: rıza yoksa gönderme
    else:
        _send(n, chosen, order.id)
    db.commit()
    return n


def resend(db: Session, n: Notification, notifier: Notifier, email_notifier: Notifier | None) -> Notification:
    """Yalnızca FAILED kayıt tekrar gönderilir; sonuç aynı kayda yazılır (SENT bir kayıt iki kez gitmez)."""
    if n.status != NotificationStatus.FAILED or not n.recipient:
        return n
    order = db.get(Order, n.order_id) if n.order_id else None
    customer = order.customer if order else None
    if customer is None or not customer.contact_consent_at or n.recipient not in (customer.phone, customer.email):
        n.status = NotificationStatus.SKIPPED  # rıza geri alındı ya da iletişim bilgisi değişti
        db.commit()
        return n
    chosen = email_notifier if (email_notifier and n.channel == email_notifier.channel) else notifier
    _send(n, chosen, n.order_id)
    db.commit()
    return n
