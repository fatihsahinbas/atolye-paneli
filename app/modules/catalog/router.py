from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy.orm import Session

from app.core.db import get_db, utcnow
from app.core.deps import csrf_protect, current_user, require_owner
from app.core.templating import render
from app.core.tenancy import get_owned, scoped
from app.domain.pricing import PURITY_MILYEM, PricingError, PricingType
from app.modules.auth.models import User
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


def _page(request: Request, db: Session, user: User, **extra):
    products = db.scalars(scoped(Product, user).order_by(Product.name)).all()
    ws = db.get(Workshop, user.workshop_id)
    return render(
        request,
        "catalog/list.html",
        {"products": products, "workshop": ws, "purities": PURITY_MILYEM, **extra},
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
            purity_milyem=int(purity_milyem) if purity_milyem.strip() else None,
            labor_milyem=int(labor_milyem) if labor_milyem.strip() else None,
            extra_cost=_dec(extra_cost) or Decimal(0),
            show_in_showcase=show_in_showcase,
        )
    except (ValidationError, ValueError) as e:
        msg = first_error(e) if isinstance(e, ValidationError) else str(e)
        return _page(request, db, user, error=msg)
    db.add(Product(workshop_id=user.workshop_id, **data.model_dump()))
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
