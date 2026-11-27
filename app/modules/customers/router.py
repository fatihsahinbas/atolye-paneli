from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db import get_db, utcnow
from app.core.deps import csrf_protect, current_user, require_owner
from app.core.templating import render
from app.core.tenancy import get_owned, scoped
from app.modules.auth.models import User
from app.modules.auth.schemas import EMAIL_RE, first_error
from app.modules.customers.models import Customer, anonymized_name
from app.modules.notifications.models import Notification
from app.modules.orders.models import Order

router = APIRouter(prefix="/musteriler", tags=["customers"])


class CustomerIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if not v:
            return None
        digits = "".join(ch for ch in v if ch.isdigit() or ch == "+")
        if not 10 <= len(digits.lstrip("+")) <= 13:
            raise ValueError("Telefon numarası geçersiz")
        return digits

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("E-posta geçersiz")
        return v


def _list(request: Request, db: Session, user: User, **extra):
    customers = db.scalars(scoped(Customer, user).order_by(Customer.full_name)).all()
    return render(request, "customers/list.html", {"customers": customers, **extra})


@router.get("")
def list_customers(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _list(request, db, user)


@router.post("", dependencies=[Depends(csrf_protect)])
def create_customer(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    full_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    notes: str = Form(""),
    consent: bool = Form(False),
    marketing: bool = Form(False),
):
    try:
        data = CustomerIn(full_name=full_name.strip(), phone=phone or None, email=email or None, notes=notes or None)
    except ValidationError as e:
        return _list(request, db, user, error=first_error(e))
    db.add(
        Customer(
            workshop_id=user.workshop_id,
            **data.model_dump(),
            contact_consent_at=utcnow() if consent else None,
            marketing_consent_at=utcnow() if marketing else None,
        )
    )
    db.commit()
    return RedirectResponse("/musteriler", status_code=303)


@router.post("/{customer_id}/anonimlestir", dependencies=[Depends(csrf_protect)])
def anonymize_customer(
    customer_id: int, db: Session = Depends(get_db), user: User = Depends(require_owner)
):
    """KVKK silme talebi: sipariş geçmişi kalır, kişisel veri kalıcı olarak silinir."""
    c = get_owned(db, Customer, customer_id, user)
    c.full_name = anonymized_name(c.id)
    c.phone = c.email = c.notes = None
    c.contact_consent_at = c.marketing_consent_at = None
    # Bildirim geçmişinde de ad/telefon/e-posta kalmasın
    order_ids = select(Order.id).where(Order.customer_id == c.id, Order.workshop_id == user.workshop_id)
    db.execute(
        update(Notification)
        .where(Notification.workshop_id == user.workshop_id, Notification.order_id.in_(order_ids))
        .values(recipient=None, message="[KVKK silme talebiyle anonimleştirildi]")
    )
    db.commit()
    return RedirectResponse("/musteriler", status_code=303)


def _consent(current, given: bool):
    """İzin verildiyse ilk zaman damgası korunur; geri alınırsa None."""
    if not given:
        return None
    return current or utcnow()


@router.get("/{customer_id}/duzenle")
def edit_customer_form(
    request: Request, customer_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    c = get_owned(db, Customer, customer_id, user)
    if c.is_anonymized:
        return RedirectResponse("/musteriler", status_code=303)
    return render(request, "customers/edit.html", {"c": c})


@router.post("/{customer_id}/duzenle", dependencies=[Depends(csrf_protect)])
def update_customer(
    request: Request,
    customer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    full_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    notes: str = Form(""),
    consent: bool = Form(False),
    marketing: bool = Form(False),
):
    c = get_owned(db, Customer, customer_id, user)
    if c.is_anonymized:  # silinmiş veri eski bir formla geri yazılamaz
        return RedirectResponse("/musteriler", status_code=303)
    try:
        data = CustomerIn(full_name=full_name.strip(), phone=phone or None, email=email or None, notes=notes or None)
    except ValidationError as e:
        return render(request, "customers/edit.html", {"c": c, "error": first_error(e)})
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    c.contact_consent_at = _consent(c.contact_consent_at, consent)
    c.marketing_consent_at = _consent(c.marketing_consent_at, marketing)
    db.commit()
    return RedirectResponse("/musteriler", status_code=303)
