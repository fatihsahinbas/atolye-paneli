"""Ürün / şablon.  Sahip: Seher (vitrin) + Hayrettin (fiyat)"""
from decimal import Decimal

from sqlalchemy import Enum, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantMixin, TimestampMixin
from app.domain.pricing import PricingType


class Product(TenantMixin, TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    pricing_type: Mapped[PricingType] = mapped_column(
        Enum(PricingType, native_enum=False, length=10), default=PricingType.FIXED
    )
    # FIXED
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    # GOLD
    weight_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    purity_milyem: Mapped[int | None]
    labor_milyem: Mapped[int | None]
    # Ortak
    extra_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    is_active: Mapped[bool] = mapped_column(default=True)
    show_in_showcase: Mapped[bool] = mapped_column(default=True)
