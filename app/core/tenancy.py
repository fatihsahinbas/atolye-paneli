"""Tenant izolasyonu: bir atölye başka atölyenin kaydını ASLA göremez (IDOR koruması, #4).

Kural: tenant tablosuna erişen her sorgu scoped() veya get_owned() kullanır.
Başka atölyenin kaydı için 403 değil 404 dönülür — kaydın varlığı bile sızmaz.
"""
from fastapi import HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User


def scoped[T](model: type[T], user: User) -> Select[tuple[T]]:
    return select(model).where(model.workshop_id == user.workshop_id)  # type: ignore[attr-defined]


def get_owned[T](db: Session, model: type[T], obj_id: int, user: User) -> T:
    obj = db.scalar(scoped(model, user).where(model.id == obj_id))  # type: ignore[attr-defined]
    if obj is None:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    return obj
