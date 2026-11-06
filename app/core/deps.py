"""Kimlik, rol ve CSRF bağımlılıkları. Yetki kararı YALNIZCA sunucuda (Checklist #3, #4, #18)."""
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db, utcnow
from app.core.security import safe_equals, token_digest
from app.modules.auth.models import Role, User, UserSession

SESSION_COOKIE = "atolye_session"


class LoginRequired(Exception):
    """HTML sayfalarında giriş ekranına yönlendirmek için."""


def as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # SQLite tz bilgisini saklamaz


def load_session(request: Request, db: Session) -> UserSession | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == token_digest(token)))
    if sess is None or as_aware(sess.expires_at) < utcnow() or not sess.user.is_active:
        return None
    return sess


def current_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    sess = load_session(request, db)
    if sess is None:
        raise LoginRequired
    request.state.session = sess
    return sess


def current_user(sess: UserSession = Depends(current_session)) -> User:
    return sess.user


def require_owner(user: User = Depends(current_user)) -> User:
    if user.role != Role.OWNER:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
    return user


async def csrf_protect(request: Request, sess: UserSession = Depends(current_session)) -> None:
    """Durum değiştiren her istekte CSRF token'ı doğrula (form alanı veya HTMX başlığı)."""
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    token = request.headers.get("X-CSRF-Token")
    if not token:
        form = await request.form()
        token = form.get("csrf_token")  # type: ignore[assignment]
    if not token or not safe_equals(str(token), sess.csrf_token):
        raise HTTPException(status_code=403, detail="Geçersiz istek")
