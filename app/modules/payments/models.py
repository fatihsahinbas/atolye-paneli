"""Ödeme kayıtları ve webhook tekrar koruması.  Sahip: Hasan"""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantMixin, TimestampMixin


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"


class Payment(TenantMixin, TimestampMixin, Base):
    """Abonelik ödemesi. Kart bilgisi hiçbir zaman burada değil (sağlayıcının sayfasında)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_oid: Mapped[str] = mapped_column(String(64), unique=True)  # yalnız harf+rakam (PayTR)
    provider: Mapped[str] = mapped_column(String(20))
    plan_code: Mapped[str] = mapped_column(String(20))
    months: Mapped[int] = mapped_column(default=1)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # TL, KDV dahil
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=10), default=PaymentStatus.PENDING
    )
    provider_ref: Mapped[str | None] = mapped_column(String(200), index=True)  # iyzico token
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessedWebhook(TimestampMixin, Base):
    __tablename__ = "processed_webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(20))
    event_id: Mapped[str] = mapped_column(String(100), unique=True)
    payload: Mapped[str] = mapped_column(Text)
