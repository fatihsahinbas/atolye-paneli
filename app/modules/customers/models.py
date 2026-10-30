"""Müşteri.  Sahip: Deha (iletişim) — KVKK alanları: Hasan"""
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantMixin, TimestampMixin


class Customer(TenantMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(254))
    notes: Mapped[str | None] = mapped_column(Text)
    # Bildirim göndermek için açık rıza zamanı (KVKK). Boşsa bildirim gitmez.
    contact_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def first_name(self) -> str:
        return self.full_name.split()[0] if self.full_name else ""
