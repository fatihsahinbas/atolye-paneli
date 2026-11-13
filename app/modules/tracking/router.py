"""Müşteri sipariş takip sayfası (giriş gerektirmez).  Sahip: Deha

Erişim anahtarı = tahmin edilemez tracking_code. Sayfada yalnızca ilk ad görünür (KVKK).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templating import render
from app.domain.order_status import BOARD_ORDER, OrderStatus
from app.modules.media.models import Media
from app.modules.media.service import media_response
from app.modules.orders.models import Order
from app.modules.workshop.models import Workshop

router = APIRouter(prefix="/t", tags=["tracking"])


def _order_by_code(db: Session, code: str) -> Order:
    if not 8 <= len(code) <= 32:
        raise HTTPException(404)
    order = db.scalar(select(Order).where(Order.tracking_code == code))
    if order is None:
        raise HTTPException(404)
    return order


@router.get("/{code}")
def track(request: Request, code: str, db: Session = Depends(get_db)):
    order = _order_by_code(db, code)
    ws = db.get(Workshop, order.workshop_id)
    media = db.scalars(select(Media).where(Media.order_id == order.id, Media.is_public.is_(True))).all()
    steps = [s for s in BOARD_ORDER if s != OrderStatus.DESIGN_APPROVAL or any(
        e.to_status == OrderStatus.DESIGN_APPROVAL for e in order.events)]
    return render(
        request,
        "public/track.html",
        {"order": order, "workshop": ws, "media": media, "steps": steps, "first_name": order.customer.first_name},
    )


@router.get("/{code}/medya/{media_id}")
def track_media(request: Request, code: str, media_id: int, boyut: str | None = None, db: Session = Depends(get_db)):
    order = _order_by_code(db, code)
    m = db.scalar(
        select(Media).where(Media.id == media_id, Media.order_id == order.id, Media.is_public.is_(True))
    )
    if m is None:
        raise HTTPException(404)
    return media_response(request.app.state.settings.media_root, m, boyut)
