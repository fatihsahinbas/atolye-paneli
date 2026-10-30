"""Kullanıcı ve oturum.  Sahip: Hasan"""
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TenantMixin, TimestampMixin


class Role(StrEnum):
    OWNER = "OWNER"  # atölye sahibi: fiyat, ürün, personel, hesap silme
    STAFF = "STAFF"  # usta/personel: sipariş ve üretim


class User(TenantMixin, TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=10), default=Role.STAFF)
    is_active: Mapped[bool] = mapped_column(default=True)

    workshop = relationship("Workshop", lazy="joined")  # şablonlarda kapalı oturumda da erişilir


class UserSession(TimestampMixin, Base):
    """Sunucu taraflı oturum: çıkışta / hesap silmede anında iptal edilebilir."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(lazy="joined")
