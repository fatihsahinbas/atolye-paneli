from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import csrf_protect, current_user
from app.core.templating import render
from app.core.tenancy import get_owned, scoped
from app.domain.deadline import deadline_state, suggest_due_date
from app.domain.order_status import BOARD_ORDER, InvalidTransition, OrderStatus, allowed_next
from app.domain.pricing import PricingError
from app.modules.auth.models import User
from app.modules.catalog.models import Product
from app.modules.catalog.service import quote
from app.modules.customers.models import Customer
from app.modules.media.models import Media
from app.modules.media.service import UploadError, media_response, save_image
from app.modules.notifications.models import Notification
from app.modules.notifications.service import notify_status_change
from app.modules.orders.models import Order
from app.modules.orders.service import NewItem, change_status, create_order
from app.modules.workshop.models import Workshop

router = APIRouter(tags=["orders"])


def notify(request: Request, db: Session, order: Order) -> None:
    st = request.app.state
    notify_status_change(db, order, st.notifier, str(request.base_url), getattr(st, "email_notifier", None))

MAX_ITEMS = 50


@router.get("/")
def board(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Üretim panosu (kanban)."""
    orders = db.scalars(
        scoped(Order, user).where(Order.status != OrderStatus.CANCELLED).order_by(Order.due_date, Order.id)
    ).all()
    columns = {s: [o for o in orders if o.status == s] for s in BOARD_ORDER}
    today = date.today()
    states = {o.id: deadline_state(o.due_date, today, o.status) for o in orders}
    return render(request, "orders/board.html", {"columns": columns, "today": today, "deadline": states})


def _new_form(request: Request, db: Session, user: User, **extra):
    customers = db.scalars(scoped(Customer, user).order_by(Customer.full_name)).all()
    products = _active_products(db, user)
    return render(request, "orders/new.html", {"customers": customers, "products": products, **extra})


@router.get("/siparisler/yeni")
def new_order_form(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _new_form(request, db, user)


def _active_products(db: Session, user: User):
    return db.scalars(scoped(Product, user).where(Product.is_active.is_(True)).order_by(Product.name)).all()


def _parse_items(product_id: list[int], quantity: list[int], description: list[str]) -> list[NewItem]:
    """Formdaki paralel listeleri kalemlere çevirir. Hatalıysa ValueError."""
    if not product_id:
        raise ValueError("En az bir ürün eklemelisiniz")
    if len(product_id) != len(quantity):
        raise ValueError("Ürün ve adet bilgileri eşleşmiyor")
    if len(product_id) > MAX_ITEMS:
        raise ValueError(f"En fazla {MAX_ITEMS} kalem eklenebilir")
    description = description + [""] * (len(product_id) - len(description))
    items = []
    for pid, qty, desc in zip(product_id, quantity, description[: len(product_id)], strict=True):
        if not 1 <= qty <= 1000:
            raise ValueError("Adet 1 ile 1000 arasında olmalıdır")
        items.append(NewItem(pid, qty, desc.strip()[:200] or None))
    return items


@router.get("/siparisler/kalem/yeni")
def new_item_row(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """HTMX: forma yeni kalem satırı."""
    products = _active_products(db, user)
    if not products:
        raise HTTPException(400, "Aktif ürün yok")
    return render(request, "orders/_item_row.html", {"products": products})


@router.get("/siparisler/termin-onerisi")
def due_date_suggestion(
    urun: list[int] = Query([]),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Kalemlerdeki en uzun üretim süresinden termin önerisi (iş günü). Öneri yoksa null."""
    days = [get_owned(db, Product, pid, user).avg_production_days for pid in urun[:MAX_ITEMS]]
    due = suggest_due_date(date.today(), days)
    return JSONResponse({"due_date": due.isoformat() if due else None})


@router.post("/siparisler/kalem/sil", dependencies=[Depends(csrf_protect)])
def remove_item_row():
    """HTMX: satır istemcide silinir (hx-swap=delete); sunucu yalnızca 200 döner."""
    return Response(status_code=200)


@router.post("/siparisler/fiyat-onizleme", dependencies=[Depends(csrf_protect)])
def order_price_preview(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    product_id: list[int] = Form([]),
    quantity: list[int] = Form([]),
):
    """HTMX: kalemlerin toplamı. Hesap create_order ile aynı (quote × adet)."""
    total_net = total_gross = Decimal(0)
    error = None
    try:
        items = _parse_items(product_id, quantity, [])
        workshop = db.get(Workshop, user.workshop_id)
        for it in items:
            product = get_owned(db, Product, it.product_id, user)
            if not product.is_active:
                raise ValueError("Pasif ürün siparişe eklenemez")
            line = quote(product, workshop, 1).times(it.quantity)
            total_net += line.net
            total_gross += line.gross
    except (PricingError, ValueError) as e:
        error = str(e)
    return render(
        request, "orders/_total.html", {"total_net": total_net, "total_gross": total_gross, "error": error}
    )


@router.post("/siparisler", dependencies=[Depends(csrf_protect)])
def create_order_view(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    customer_id: int = Form(...),
    product_id: list[int] = Form([]),
    quantity: list[int] = Form([]),
    description: list[str] = Form([]),
    due_date: date | None = Form(None),
    note: str = Form("", max_length=2000),
):
    try:
        items = _parse_items(product_id, quantity, description)
        order = create_order(db, user, customer_id, items, due_date, note.strip() or None)
    except (PricingError, ValueError) as e:
        db.rollback()
        return _new_form(request, db, user, error=str(e))
    return RedirectResponse(f"/siparisler/{order.id}", status_code=303)


@router.get("/siparisler/{order_id}")
def order_detail(request: Request, order_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    order = get_owned(db, Order, order_id, user)
    media = db.scalars(select(Media).where(Media.order_id == order.id, Media.workshop_id == user.workshop_id)).all()
    notifications = db.scalars(
        scoped(Notification, user).where(Notification.order_id == order.id).order_by(Notification.id.desc())
    ).all()
    return render(
        request,
        "orders/detail.html",
        {"order": order, "next_statuses": allowed_next(order.status), "media": media,
         "notifications": notifications,
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
    notify(request, db, order)
    return RedirectResponse(f"/siparisler/{order.id}", status_code=303)


@router.post("/siparisler/{order_id}/tasi", dependencies=[Depends(csrf_protect)])
def order_move(
    request: Request,
    order_id: int,
    to_status: OrderStatus = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Panoda sürükle-bırak. Karar sunucuda: geçersiz geçiş → 409, kart eski yerine döner."""
    order = get_owned(db, Order, order_id, user)
    try:
        change_status(db, user, order, to_status, None)
    except InvalidTransition:
        return JSONResponse({"ok": False, "message": "Bu durum geçişine izin verilmiyor"}, status_code=409)
    notify(request, db, order)
    return JSONResponse({"ok": True, "status": order.status.value})


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
def media_file(
    request: Request,
    media_id: int,
    boyut: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    m = get_owned(db, Media, media_id, user)
    return media_response(request.app.state.settings.media_root, m, boyut)
