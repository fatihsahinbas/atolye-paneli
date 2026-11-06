"""Atölye (tenant).  Sahip: Hasan"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Workshop(TimestampMixin, Base):
    __tablename__ = "workshops"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("20"))

    # Kuyumcular için: günlük has altın gram fiyatı (elle girilir; ileride API)
    gold_price_per_gram: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    gold_price_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
