"""H3: 30 dakikalık, tek kullanımlık şifre sıfırlama akışı."""
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.deps import as_aware
from app.core.security import hash_password, new_token, safe_equals, token_digest
from app.modules.auth.models import PasswordResetToken, User, UserSession

RESET_TOKEN_MINUTES = 30


def generate_reset_token():
    token = new_token()
    return token, token_digest(token), utcnow() + timedelta(minutes=RESET_TOKEN_MINUTES)


def is_reset_token_valid(stored_hash, token, expires_at, used=False):
    if used or not token or not stored_hash or expires_at is None:
        return False
    return safe_equals(token_digest(token), stored_hash) and utcnow() < as_aware(expires_at)


def request_reset(db: Session, email: str, base_url: str, sender) -> None:
    """Var olmayan/inaktif hesap için hiçbir bilgi sızdırmaz."""
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is None:
        return
    token, hashed, expires = generate_reset_token()
    # Aynı hesaba yeni talep önceki bütün bağlantıları geçersiz kılar.
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    db.add(PasswordResetToken(user_id=user.id, token_hash=hashed, expires_at=expires))
    db.commit()
    link = f"{base_url.rstrip('/')}/sifre-yenile?token={quote(token)}"
    sender(user.email, link)


def valid_reset(db: Session, token: str) -> PasswordResetToken | None:
    if not token or len(token) > 256:
        return None
    candidate = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_digest(token)))
    if candidate is None or not candidate.user.is_active:
        return None
    if not is_reset_token_valid(candidate.token_hash, token, candidate.expires_at, candidate.used_at is not None):
        return None
    return candidate


def complete_reset(db: Session, token: str, password: str) -> bool:
    # Row lock PostgreSQL'de eşzamanlı kullanımları engeller; SQLite yazma işlemini seri hale getirir.
    candidate = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_digest(token)
    ).with_for_update()) if token and len(token) <= 256 else None
    if candidate is None or not candidate.user.is_active or not is_reset_token_valid(
        candidate.token_hash, token, candidate.expires_at, candidate.used_at is not None
    ):
        db.rollback()
        return False
    candidate.user.password_hash = hash_password(password)
    candidate.used_at = utcnow()
    db.execute(delete(UserSession).where(UserSession.user_id == candidate.user_id))
    db.commit()
    return True
