from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy.orm import Session

from app.core.db import get_db, utcnow
from app.core.deps import csrf_protect, current_user, require_owner
from app.core.templating import render
from app.core.tenancy import get_owned, scoped
from app.domain.plans import public_plans
from app.domain.pricing import PURITY_MILYEM, PricingError, PricingType
from app.modules.auth.models import Role, User
from app.modules.auth.schemas import first_error
from app.modules.catalog.models import Product
from app.modules.catalog.service import quote
from app.modules.workshop.models import Workshop

router = APIRouter(tags=["catalog"])


class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    pricing_type: PricingType
    base_price: Decimal | None = Field(default=None, ge=0, le=Decimal("10000000"))
    weight_g: Decimal | None = Field(default=None, gt=0, le=Decimal("10000"))
    purity_milyem: int | None = Field(default=None, gt=0, le=1000)
    labor_milyem: int | None = Field(default=None, ge=0, le=500)
    extra_cost: Decimal = Field(default=Decimal(0), ge=0, le=Decimal("10000000"))
    is_active: bool = True
    show_in_showcase: bool = True

    @model_validator(mode="after")
    def _by_type(self) -> "ProductIn":
        if self.pricing_type == PricingType.FIXED and self.base_price is None:
            raise ValueError("Sabit fiyatlı üründe fiyat zorunlu")
        if self.pricing_type == PricingType.GOLD and (self.weight_g is None or self.purity_milyem is None):
            raise ValueError("Altın üründe gram ve ayar zorunlu")
        if self.pricing_type == PricingType.GOLD_COST_PLUS:
            # Fiyat motoru hazır; ürün alanları + migration (kolon 10 → 20 karakter) gelince açılacak.
            raise ValueError("Maliyet + kâr fiyatlaması henüz desteklenmiyor")
        return self


def _dec(v: str) -> Decimal | None:
    v = v.strip().replace(",", ".")
    if not v:
        return None
    try:
        return Decimal(v)
    except InvalidOperation:
        raise ValueError("Sayı formatı geçersiz") from None


def _int_or_none(v: str) -> int | None:
    s = v.strip()
    if not s:
        return None
    return int(s)


def _page(request: Request, db: Session, user: User, **extra):
    products = db.scalars(scoped(Product, user).order_by(Product.name)).all()
    ws = db.get(Workshop, user.workshop_id)
    return render(
        request,
        "catalog/list.html",
        {"products": products, "workshop": ws, "purities": PURITY_MILYEM, **extra},
    )


def _edit_page(request: Request, db: Session, user: User, product: Product, **extra):
    ws = db.get(Workshop, user.workshop_id)
    return render(
        request,
        "catalog/edit.html",
        {"product": product, "workshop": ws, "purities": PURITY_MILYEM, **extra},
    )


@router.get("/urunler")
def list_products(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _page(request, db, user)


@router.post("/urunler", dependencies=[Depends(csrf_protect)])
def create_product(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_owner),
    name: str = Form(""),
    description: str = Form(""),
    pricing_type: str = Form("FIXED"),
    base_price: str = Form(""),
    weight_g: str = Form(""),
    purity_milyem: str = Form(""),
    labor_milyem: str = Form(""),
    extra_cost: str = Form("0"),
    show_in_showcase: bool = Form(False),
):
    try:
        data = ProductIn(
            name=name.strip(),
            description=description.strip() or None,
            pricing_type=pricing_type,
            base_price=_dec(base_price),
            weight_g=_dec(weight_g),
            purity_milyem=_int_or_none(purity_milyem),
            labor_milyem=_int_or_none(labor_milyem),
            extra_cost=_dec(extra_cost) or Decimal(0),
            is_active=True,
            show_in_showcase=show_in_showcase,
        )
    except (ValidationError, ValueError) as e:
        msg = first_error(e) if isinstance(e, ValidationError) else str(e)
        return _page(request, db, user, error=msg)
    db.add(Product(workshop_id=user.workshop_id, **data.model_dump()))
    db.commit()
    return RedirectResponse("/urunler", status_code=303)


@router.get("/urunler/{product_id}/duzenle")
def edit_product_form(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role != Role.OWNER:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
    product = get_owned(db, Product, product_id, user)
    return _edit_page(request, db, user, product)


@router.post("/urunler/{product_id}/duzenle", dependencies=[Depends(csrf_protect)])
def update_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    name: str = Form(""),
    description: str = Form(""),
    pricing_type: str = Form("FIXED"),
    base_price: str = Form(""),
    weight_g: str = Form(""),
    purity_milyem: str = Form(""),
    labor_milyem: str = Form(""),
    extra_cost: str = Form("0"),
    is_active: bool = Form(False),
    show_in_showcase: bool = Form(False),
):
    if user.role != Role.OWNER:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
    product = get_owned(db, Product, product_id, user)
    try:
        data = ProductIn(
            name=name.strip(),
            description=description.strip() or None,
            pricing_type=pricing_type,
            base_price=_dec(base_price),
            weight_g=_dec(weight_g),
            purity_milyem=_int_or_none(purity_milyem),
            labor_milyem=_int_or_none(labor_milyem),
            extra_cost=_dec(extra_cost) or Decimal(0),
            is_active=is_active,
            show_in_showcase=show_in_showcase,
        )
    except (ValidationError, ValueError) as e:
        db.rollback()
        msg = first_error(e) if isinstance(e, ValidationError) else str(e)
        return _edit_page(request, db, user, product, error=msg)

    for field, value in data.model_dump().items():
        setattr(product, field, value)
    db.commit()
    return RedirectResponse("/urunler", status_code=303)


@router.get("/urunler/{product_id}/fiyat")
def price_preview(
    request: Request,
    product_id: int,
    adet: int = Query(1, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """HTMX parçası: sipariş formunda canlı fiyat önizlemesi."""
    product = get_owned(db, Product, product_id, user)
    ws = db.get(Workshop, user.workshop_id)
    try:
        bd, err = quote(product, ws, adet), None
    except PricingError as e:
        bd, err = None, str(e)
    return render(request, "catalog/_price.html", {"bd": bd, "error": err})


@router.post("/atolye/altin-fiyati", dependencies=[Depends(csrf_protect)])
def set_gold_price(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_owner),
    price: str = Form(""),
):
    try:
        value = _dec(price)
        if value is None or not Decimal(1) <= value <= Decimal(1_000_000):
            raise ValueError("Geçerli bir gram fiyatı girin")
    except ValueError as e:
        return _page(request, db, user, error=str(e))
    ws = db.get(Workshop, user.workshop_id)
    ws.gold_price_per_gram = value
    ws.gold_price_updated_at = utcnow()
    db.commit()
    return RedirectResponse("/urunler", status_code=303)


@router.get("/fiyatlar")
def pricing_page(request: Request):
    """Herkese açık paket ve fiyatlandırma sayfası (giriş gerektirmez)."""
    return render(
        request,
        "public/pricing.html",
        {"plans": public_plans()},
    )
