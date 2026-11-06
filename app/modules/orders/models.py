"""Sipariş, kalem, durum geçmişi.  Sahip: Çınar"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TenantMixin, TimestampMixin, utcnow
from app.domain.order_status import OrderStatus

_status_type = Enum(OrderStatus, native_enum=False, length=20)


class Order(TenantMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Siparişli müşteri uygulamada silinmez, anonimleştirilir (KVKK). CASCADE yalnızca atölye silinirken devreye girer.
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    # Müşteriye giden takip linki: tahmin edilemez, sıralı ID değil (IDOR koruması)
    tracking_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[OrderStatus] = mapped_column(_status_type, default=OrderStatus.RECEIVED, index=True)
    due_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    total_net: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    total_gross: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal(0))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    customer = relationship("Customer")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    events: Mapped[list["OrderEvent"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderEvent.id"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    description: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(default=1)
    # Sipariş anındaki fiyat dondurulur (altın fiyatı sonra değişse de tutar sabit kalır)
    unit_net: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_net: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_gross: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped[Order] = relationship(back_populates="items")


class OrderEvent(TimestampMixin, Base):
    """Durum geçmişi — müşteri takip ekranındaki zaman çizelgesi buradan gelir."""

    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[OrderStatus | None] = mapped_column(_status_type)
    to_status: Mapped[OrderStatus] = mapped_column(_status_type)
    note: Mapped[str | None] = mapped_column(String(300))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    order: Mapped[Order] = relationship(back_populates="events")
