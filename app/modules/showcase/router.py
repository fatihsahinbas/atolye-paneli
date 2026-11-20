"""Atölye vitrin sayfası /v/{slug} (giriş gerektirmez).  Sahip: Seher"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templating import render
from app.domain.pricing import PricingError
from app.modules.catalog.models import Product
from app.modules.catalog.service import quote
from app.modules.notifications.service import normalize_phone
from app.modules.workshop.models import Workshop

router = APIRouter(prefix="/v", tags=["showcase"])


@router.get("/{slug}")
def showcase(request: Request, slug: str, db: Session = Depends(get_db)):
    ws = db.scalar(select(Workshop).where(Workshop.slug == slug[:60]))
    if ws is None:
        raise HTTPException(404)
    products = db.scalars(
        select(Product)
        .where(Product.workshop_id == ws.id, Product.is_active.is_(True), Product.show_in_showcase.is_(True))
        .order_by(Product.name)
    ).all()
    cards = []
    for p in products:
        try:
            price = quote(p, ws).gross
        except PricingError:
            price = None  # "Fiyat için sorunuz"
        cards.append({"product": p, "price": price})
    return render(request, "public/showcase.html", {"workshop": ws, "cards": cards, "wa_phone": _wa_phone(ws.phone)})


def _wa_phone(raw: str | None) -> str | None:
    """wa.me için yalnız rakamlar (905321112233). Telefon yoksa ya da geçersizse buton gösterilmez."""
    if not raw:
        return None
    try:
        return normalize_phone(raw).lstrip("+")
    except ValueError:
        return None
