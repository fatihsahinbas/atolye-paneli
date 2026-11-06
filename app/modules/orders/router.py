from datetime import date

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import csrf_protect, current_user
from app.core.templating import render
from app.core.tenancy import get_owned, scoped
from app.domain.order_status import BOARD_ORDER, InvalidTransition, OrderStatus, allowed_next
from app.domain.pricing import PricingError
from app.modules.auth.models import User
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.media.models import Media
from app.modules.media.service import UploadError, media_path, save_image
from app.modules.notifications.service import notify_status_change
from app.modules.orders.models import Order
from app.modules.orders.service import NewItem, change_status, create_order

router = APIRouter(tags=["orders"])


@router.get("/")
def board(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Üretim panosu (kanban)."""
    orders = db.scalars(
        scoped(Order, user).where(Order.status != OrderStatus.CANCELLED).order_by(Order.due_date, Order.id)
    ).all()
    columns = {s: [o for o in orders if o.status == s] for s in BOARD_ORDER}
    return render(request, "orders/board.html", {"columns": columns, "today": date.today()})


def _new_form(request: Request, db: Session, user: User, **extra):
    customers = db.scalars(scoped(Customer, user).order_by(Customer.full_name)).all()
    products = db.scalars(scoped(Product, user).where(Product.is_active.is_(True)).order_by(Product.name)).all()
    return render(request, "orders/new.html", {"customers": customers, "products": products, **extra})


@router.get("/siparisler/yeni")
def new_order_form(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _new_form(request, db, user)


@router.post("/siparisler", dependencies=[Depends(csrf_protect)])
def create_order_view(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    customer_id: int = Form(...),
    product_id: int = Form(...),
    quantity: int = Form(1, ge=1, le=1000),
    description: str = Form("", max_length=200),
    due_date: date | None = Form(None),
    note: str = Form("", max_length=2000),
):
    try:
        order = create_order(
            db, user, customer_id, [NewItem(product_id, quantity, description.strip() or None)],
            due_date, note.strip() or None,
        )
    except (PricingError, ValueError) as e:
        db.rollback()
        return _new_form(request, db, user, error=str(e))
    return RedirectResponse(f"/siparisler/{order.id}", status_code=303)


@router.get("/siparisler/{order_id}")
def order_detail(request: Request, order_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    order = get_owned(db, Order, order_id, user)
    media = db.scalars(select(Media).where(Media.order_id == order.id, Media.workshop_id == user.workshop_id)).all()
    return render(
        request,
        "orders/detail.html",
        {"order": order, "next_statuses": allowed_next(order.status), "media": media,
         "tracking_url": f"{str(request.base_url).rstrip('/')}/t/{order.tracking_code}"},
    )


@router.post("/siparisler/{order_id}/durum", dependencies=[Depends(csrf_protect)])
def order_status(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    to_status: OrderStatus = Form(...),
    note: str = Form("", max_length=300),
):
    order = get_owned(db, Order, order_id, user)
    try:
        change_status(db, user, order, to_status, note.strip() or None)
    except InvalidTransition:
        return RedirectResponse(f"/siparisler/{order.id}", status_code=303)
    notify_status_change(db, order, request.app.state.notifier, str(request.base_url))
    return RedirectResponse(f"/siparisler/{order.id}", status_code=303)


@router.post("/siparisler/{order_id}/medya", dependencies=[Depends(csrf_protect)])
async def order_media(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    file: UploadFile = File(...),
    caption: str = Form("", max_length=200),
    is_public: bool = Form(False),
):
    order = get_owned(db, Order, order_id, user)
    s = request.app.state.settings
    try:
        name, ctype, size = await save_image(file, s.media_root, s.max_upload_bytes)
    except UploadError as e:
        return render(request, "errors/message.html", {"message": str(e), "back": f"/siparisler/{order.id}"}, 400)
    db.add(Media(workshop_id=user.workshop_id, order_id=order.id, stored_name=name, content_type=ctype,
                 size_bytes=size, caption=caption.strip() or None, is_public=is_public))
    db.commit()
    return RedirectResponse(f"/siparisler/{order.id}", status_code=303)


@router.get("/medya/{media_id}")
def media_file(request: Request, media_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = get_owned(db, Media, media_id, user)
    return FileResponse(media_path(request.app.state.settings.media_root, m.stored_name), media_type=m.content_type)
