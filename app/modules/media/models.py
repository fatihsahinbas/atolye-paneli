"""Medya (üretim aşaması fotoğrafları, ürün görselleri).  Sahip: Alper"""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TenantMixin, TimestampMixin


class Media(TenantMixin, TimestampMixin, Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    stored_name: Mapped[str] = mapped_column(String(64), unique=True)  # uuid + uzantı, kullanıcı adı DEĞİL
    content_type: Mapped[str] = mapped_column(String(40))
    size_bytes: Mapped[int]
    caption: Mapped[str | None] = mapped_column(String(200))
    is_public: Mapped[bool] = mapped_column(default=True)  # takip linkinde müşteri görsün mü
