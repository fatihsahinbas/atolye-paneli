"""Bildirim geçmişi: başarısızı tekrar gönder.  Sahip: Deha (H3 PROJE 6)"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import csrf_protect, current_user
from app.core.tenancy import get_owned
from app.modules.auth.models import User
from app.modules.notifications.models import Notification
from app.modules.notifications.service import resend

router = APIRouter(tags=["notifications"])


@router.post("/bildirimler/{notification_id}/tekrar", dependencies=[Depends(csrf_protect)])
def retry_notification(
    request: Request, notification_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    n = get_owned(db, Notification, notification_id, user)  # başka atölyenin kaydı → 404
    st = request.app.state
    resend(db, n, st.notifier, getattr(st, "email_notifier", None))
    back = f"/siparisler/{n.order_id}" if n.order_id else "/"
    return RedirectResponse(back, status_code=303)
