"""Ödeme webhook kayıtları (tekrar oynatma koruması).  Sahip: Hasan"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class ProcessedWebhook(TimestampMixin, Base):
    __tablename__ = "processed_webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(20))
    event_id: Mapped[str] = mapped_column(String(100), unique=True)
    payload: Mapped[str] = mapped_column(Text)
