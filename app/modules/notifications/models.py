"""Bildirim outbox'ı.  Sahip: Deha

Her bildirim önce tabloya yazılır (PENDING), sonra kanal adaptörü gönderir.
Gönderim hatası siparişi bozmaz; tekrar denenebilir.
"""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantMixin, TimestampMixin


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"  # rıza yok / iletişim bilgisi yok


class Notification(TenantMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20))  # console | whatsapp | email | sms
    recipient: Mapped[str | None] = mapped_column(String(254))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, native_enum=False, length=10), default=NotificationStatus.PENDING
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
