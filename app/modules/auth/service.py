"""Kayıt, giriş, oturum, hesap silme iş kuralları.  Sahip: Hasan"""
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.security import DUMMY_HASH, hash_password, new_token, token_digest, verify_password
from app.modules.auth.models import Role, User, UserSession
from app.modules.auth.schemas import LoginIn, RegisterIn
from app.modules.media.models import Media
from app.modules.workshop.models import Workshop


class AuthError(Exception):
    pass


def register_workshop(db: Session, data: RegisterIn) -> User:
    if db.scalar(select(Workshop.id).where(Workshop.slug == data.slug)):
        raise AuthError("Bu atölye adresi kullanımda")
    if db.scalar(select(User.id).where(User.email == data.email)):
        # Genel mesaj: hangi e-postanın kayıtlı olduğu sızmasın
        raise AuthError("Kayıt tamamlanamadı, bilgileri kontrol edin")
    ws = Workshop(name=data.workshop_name, slug=data.slug)
    db.add(ws)
    db.flush()
    user = User(
        workshop_id=ws.id,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=Role.OWNER,
    )
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, data: LoginIn) -> User:
    user = db.scalar(select(User).where(User.email == data.email))
    if user is None:
        verify_password(DUMMY_HASH, data.password)  # sabit süre
        raise AuthError("E-posta veya şifre hatalı")
    if not user.is_active or not verify_password(user.password_hash, data.password):
        raise AuthError("E-posta veya şifre hatalı")
    return user


def create_session(db: Session, user: User, ttl_hours: int) -> str:
    token = new_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=token_digest(token),
            csrf_token=new_token(24),
            expires_at=utcnow() + timedelta(hours=ttl_hours),
        )
    )
    db.commit()
    return token


def destroy_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == token_digest(token)))
        db.commit()


def delete_account(db: Session, user: User, password: str, media_root: str) -> None:
    """Gerçek silme (Checklist #21).

    OWNER → atölye ve TÜM verisi (müşteri, sipariş, medya dosyaları) silinir.
    STAFF → yalnızca kendi hesabı silinir.
    Oturumlar CASCADE ile düşer.
    """
    if not verify_password(user.password_hash, password):
        raise AuthError("Şifre hatalı")
    if user.role == Role.OWNER:
        names = db.scalars(select(Media.stored_name).where(Media.workshop_id == user.workshop_id)).all()
        db.execute(delete(Workshop).where(Workshop.id == user.workshop_id))
        db.commit()
        for name in names:
            (Path(media_root) / name).unlink(missing_ok=True)
    else:
        db.execute(delete(User).where(User.id == user.id))
        db.commit()
