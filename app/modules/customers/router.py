from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from app.core.db import get_db, utcnow
from app.core.deps import csrf_protect, current_user, require_owner
from app.core.templating import render
from app.core.tenancy import get_owned, scoped
from app.modules.auth.models import User
from app.modules.auth.schemas import EMAIL_RE, first_error
from app.modules.customers.models import Customer

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
    c.full_name = f"Silinmiş Müşteri #{c.id}"
    c.phone = c.email = c.notes = None
    c.contact_consent_at = None
    db.commit()
    return RedirectResponse("/musteriler", status_code=303)
