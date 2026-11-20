from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_workshop, verify_csrf
from app.services.notification_service import retry_notification
from app.notifiers.multi import MultiNotifier

router = APIRouter()


def get_notifier(request: Request) -> MultiNotifier:
    return request.app.state.notifier


@router.post("/bildirimler/{notification_id}/tekrar")
def retry(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    workshop=Depends(get_current_workshop),
    _=Depends(verify_csrf),
):
    result = retry_notification(notification_id, get_notifier(request), db, workshop)
    if result is None:
        raise HTTPException(status_code=404)
    return {"id": result.id, "channel": result.channel, "status": result.status}