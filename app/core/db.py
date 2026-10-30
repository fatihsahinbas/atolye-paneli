"""Veritabanı bağlantısı. Tüm sorgular SQLAlchemy ile parametreli (Checklist #15)."""
from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import DateTime, ForeignKey, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TenantMixin:
    """Atölyeye ait her tablo bu mixin'i alır. Sorgular daima workshop_id ile filtrelenir."""

    workshop_id: Mapped[int] = mapped_column(
        ForeignKey("workshops.id", ondelete="CASCADE"), index=True
    )


def build_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # SQLite'ta ON DELETE CASCADE için şart
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


def build_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    db: Session = request.app.state.SessionLocal()
    try:
        yield db
    finally:
        db.close()
