"""Atölye personeli yönetimi: yalnızca OWNER; tüm işlemler tenant kapsamlı."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import csrf_protect, require_owner
from app.core.security import hash_password
from app.core.templating import render
from app.modules.auth.models import Role, User, UserSession
from app.modules.auth.schemas import _email, first_error

router = APIRouter(prefix="/personel", tags=["staff"])


class StaffIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128)

    _normalize_email = field_validator("email")(_email)

    @field_validator("full_name")
    @classmethod
    def trim_name(cls, name: str) -> str:
        return name.strip()


def staff_page(request: Request, db: Session, owner: User, error: str | None = None, status: int = 200):
    members = db.scalars(select(User).where(User.workshop_id == owner.workshop_id).order_by(User.id)).all()
    return render(request, "auth/staff.html", {"members": members, "error": error}, status)


@router.get("")
def list_staff(request: Request, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    return staff_page(request, db, owner)


@router.post("", dependencies=[Depends(csrf_protect)])
def add_staff(
    request: Request,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
    full_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
):
    try:
        data = StaffIn(full_name=full_name, email=email, password=password)
    except ValidationError as exc:
        return staff_page(request, db, owner, first_error(exc), 422)
    member = User(
        workshop_id=owner.workshop_id,
        full_name=data.full_name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=Role.STAFF,
        is_active=True,
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return staff_page(request, db, owner, "Bu e-posta adresi zaten kullanılıyor.", 409)
    return RedirectResponse("/personel", status_code=303)


@router.post("/{member_id}/durum", dependencies=[Depends(csrf_protect)])
def toggle_staff(
    member_id: int,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    member = db.scalar(select(User).where(
        User.id == member_id,
        User.workshop_id == owner.workshop_id,
        User.role == Role.STAFF,
    ))
    if member is None:
        raise HTTPException(status_code=404)
    member.is_active = not member.is_active
    if not member.is_active:
        for sess in db.scalars(select(UserSession).where(UserSession.user_id == member.id)).all():
            db.delete(sess)
    db.commit()
    return RedirectResponse("/personel", status_code=303)
