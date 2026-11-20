from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_workshop, verify_csrf, get_owned
from app.models.order import Order
from app.services.notification_service import notify_status_change
from app.notifiers.multi import MultiNotifier

router = APIRouter()


def get_notifier(request: Request) -> MultiNotifier:
    return request.app.state.notifier


@router.post("/orders/{order_id}/status")
def update_status(
    order_id: int,
    new_status: str,
    request: Request,
    db: Session = Depends(get_db),
    workshop=Depends(get_current_workshop),
    _=Depends(verify_csrf),
):
    order = get_owned(db, Order, order_id, workshop)
    order.status = new_status
    db.commit()
    db.refresh(order)

    notif = notify_status_change(order, get_notifier(request), db)
    return {"order_id": order.id, "status": order.status, "notification": notif.status, "channel": notif.channel}