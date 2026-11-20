from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))      # SMS / EMAIL / SKIPPED
    status: Mapped[str] = mapped_column(String(20))       # SENT / FAILED / SKIPPED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    order = relationship("Order", back_populates="notifications")