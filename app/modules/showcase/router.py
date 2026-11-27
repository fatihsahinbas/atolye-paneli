"""Atölye vitrin sayfası /v/{slug} (giriş gerektirmez).  Sahip: Seher"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templating import render
from app.domain.pricing import PricingError
from app.modules.catalog.models import Product
from app.modules.catalog.service import quote
from app.modules.media.models import Media
from app.modules.media.service import cover_url, media_response
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
    covers = dict(db.execute(
        select(Media.product_id, Media.id).where(
            Media.workshop_id == ws.id, Media.is_cover.is_(True), Media.product_id.in_([p.id for p in products])
        )
    ).all())
    cards = []
    for p in products:
        try:
            price = quote(p, ws).gross
        except PricingError:
            price = None  # "Fiyat için sorunuz"
        cards.append({"product": p, "price": price, "cover": cover_url(p, ws.slug, covers)})
    return render(request, "public/showcase.html", {"workshop": ws, "cards": cards, "wa_phone": _wa_phone(ws.phone)})


@router.get("/{slug}/gorsel/{media_id}")
def showcase_image(request: Request, slug: str, media_id: int, boyut: str | None = None,
                   db: Session = Depends(get_db)):
    """Herkese açık ürün görseli: yalnız o atölyenin, aktif ve vitrinde olan ürününün görseli."""
    m = db.scalar(
        select(Media)
        .join(Product, Product.id == Media.product_id)
        .join(Workshop, Workshop.id == Media.workshop_id)
        .where(
            Workshop.slug == slug[:60], Media.id == media_id, Product.workshop_id == Media.workshop_id,
            Product.is_active.is_(True), Product.show_in_showcase.is_(True),
        )
    )
    if m is None:
        raise HTTPException(404)
    return media_response(request.app.state.settings.media_root, m, boyut)


def _wa_phone(raw: str | None) -> str | None:
    """wa.me için yalnız rakamlar (905321112233). Telefon yoksa ya da geçersizse buton gösterilmez."""
    if not raw:
        return None
    try:
        return normalize_phone(raw).lstrip("+")
    except ValueError:
        return None
