
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
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
from app.modules.catalog.service import quote
from app.modules.customers.models import Customer
from app.modules.media.models import Media
from app.modules.media.service import UploadError, media_path, save_image
from app.modules.notifications.service import notify_status_change
from app.modules.orders.models import Order
from app.modules.orders.service import NewItem, change_status, create_order
from app.modules.workshop.models import Workshop

router = APIRouter(tags=["orders"])


@router.get("/")
def board(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Üretim panosu (kanban)."""
    orders = db.scalars(
        scoped(Order, user)
        .where(Order.status != OrderStatus.CANCELLED)
        .order_by(Order.due_date, Order.id)
    ).all()

    columns = {s: [o for o in orders if o.status == s] for s in BOARD_ORDER}

    return render(
        request,
        "orders/board.html",
        {"columns": columns, "today": date.today()},
    )


def _new_form(request: Request, db: Session, user: User, **extra):
    customers = db.scalars(
        scoped(Customer, user).order_by(Customer.full_name)
    ).all()

    products = db.scalars(
        scoped(Product, user)
        .where(Product.is_active.is_(True))
        .order_by(Product.name)
    ).all()

    return render(
        request,
        "orders/new.html",
        {
            "customers": customers,
            "products": products,
            **extra,
        },
    )


@router.get("/siparisler/yeni")
def new_order_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return _new_form(request, db, user)


@router.get("/siparisler/kalem/yeni")
def add_order_item(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    products = db.scalars(
        scoped(Product, user)
        .where(Product.is_active.is_(True))
        .order_by(Product.name)
    ).all()

    if not products:
        raise HTTPException(status_code=400, detail="Aktif ürün bulunamadı")

    return render(
        request,
        "orders/_item_row.html",
        {"products": products},
    )


@router.post(
    "/siparisler/kalem/sil",
    dependencies=[Depends(csrf_protect)],
)
def remove_order_item():
    return Response(status_code=200)


@router.post(
    "/siparisler/fiyat-onizleme",
    dependencies=[Depends(csrf_protect)],
)
def order_price_preview(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    product_id: list[int] = Form([]),
    quantity: list[int] = Form([]),
):
    if len(product_id) != len(quantity):
        raise HTTPException(400, "Ürün ve adet bilgileri eşleşmiyor")

    if len(product_id) > 50:
        raise HTTPException(400, "En fazla 50 kalem eklenebilir")

    workshop = db.get(Workshop, user.workshop_id)

    if workshop is None:
        raise HTTPException(404, "Atölye bulunamadı")

    total_net = Decimal("0")
    total_gross = Decimal("0")

    try:
        for pid, qty in zip(product_id, quantity):
            if qty < 1 or qty > 1000:
                raise ValueError("Adet 1 ile 1000 arasında olmalıdır")

            product = get_owned(db, Product, pid, user)

            if not product.is_active:
                raise ValueError("Pasif ürün siparişe eklenemez")

            unit = quote(product, workshop, 1)
            line = unit.times(qty)

            total_net += line.net
            total_gross += line.gross

    except (PricingError, ValueError) as exc:
        return render(
            request,
            "orders/_total.html",
            {
                "total_net": total_net,
                "total_gross": total_gross,
                "error": str(exc),
            },
        )

    return render(
        request,
        "orders/_total.html",
        {
            "total_net": total_net,
            "total_gross": total_gross,
            "error": None,
        },
    )


@router.post(
    "/siparisler",
    dependencies=[Depends(csrf_protect)],
)
def create_order_view(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    customer_id: int = Form(...),
    product_id: list[int] = Form(...),
    quantity: list[int] = Form(...),
    description: list[str] = Form([]),
    due_date: date | None = Form(None),
    note: str = Form("", max_length=2000),
):
    try:
        if not product_id:
            raise ValueError("En az bir ürün eklemelisiniz.")

        if len(product_id) != len(quantity):
            raise ValueError("Ürün ve adet bilgileri eşleşmiyor.")

        if len(product_id) > 50:
            raise ValueError("En fazla 50 kalem ekleyebilirsiniz.")

        if len(description) < len(product_id):
            description.extend([""] * (len(product_id) - len(description)))

        items = []

        for pid, qty, desc in zip(product_id, quantity, description):
            if qty < 1 or qty > 1000:
                raise ValueError("Ürün adedi 1 ile 1000 arasında olmalıdır.")

            items.append(
                NewItem(
                    product_id=pid,
                    quantity=qty,
                    description=desc.strip() or None,
                )
            )

        order = create_order(
            db,
            user,
            customer_id,
            items,
            due_date,
            note.strip() or None,
        )

    except (PricingError, ValueError) as exc:
        db.rollback()
        return _new_form(request, db, user, error=str(exc))

    return RedirectResponse(
        f"/siparisler/{order.id}",
        status_code=303,
    )


@router.get("/siparisler/{order_id}")
def order_detail(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    order = get_owned(db, Order, order_id, user)

    media = db.scalars(
        select(Media).where(
            Media.order_id == order.id,
            Media.workshop_id == user.workshop_id,
        )
    ).all()

    return render(
        request,
        "orders/detail.html",
        {
            "order": order,
            "next_statuses": allowed_next(order.status),
            "media": media,
            "tracking_url": (
                f"{str(request.base_url).rstrip('/')}"
                f"/t/{order.tracking_code}"
            ),
        },
    )


@router.post(
    "/siparisler/{order_id}/durum",
    dependencies=[Depends(csrf_protect)],
)
def order_status(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    to_status: OrderStatus = Form(...),
    note: str = Form("", max_length=300),
):
    order = get_owned(db, Order, order_id, user)
    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        change_status(
            db,
            user,
            order,
            to_status,
            note.strip() or None,
        )
    except InvalidTransition:
        if is_htmx:
            return Response(
                content="Bu durum geçişine izin verilmiyor!",
                status_code=422,
                media_type="text/plain",
            )

        return RedirectResponse(
            f"/siparisler/{order.id}",
            status_code=303,
        )

    notify_status_change(
        db,
        order,
        request.app.state.notifier,
        str(request.base_url),
    )

    if is_htmx:
        return Response(status_code=204)

    return RedirectResponse(
        f"/siparisler/{order.id}",
        status_code=303,
    )


@router.post(
    "/siparisler/{order_id}/medya",
    dependencies=[Depends(csrf_protect)],
)
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
    settings = request.app.state.settings

    try:
        name, ctype, size = await save_image(
            file,
            settings.media_root,
            settings.max_upload_bytes,
        )
    except UploadError as exc:
        return render(
            request,
            "errors/message.html",
            {
                "message": str(exc),
                "back": f"/siparisler/{order.id}",
            },
            400,
        )

    db.add(
        Media(
            workshop_id=user.workshop_id,
            order_id=order.id,
            stored_name=name,
            content_type=ctype,
            size_bytes=size,
            caption=caption.strip() or None,
            is_public=is_public,
        )
    )

    db.commit()

    return RedirectResponse(
        f"/siparisler/{order.id}",
        status_code=303,
    )


@router.get("/medya/{media_id}")
def media_file(
    request: Request,
    media_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    media = get_owned(db, Media, media_id, user)

    return FileResponse(
        media_path(
            request.app.state.settings.media_root,
            media.stored_name,
        ),
        media_type=media.content_type,
    )
