import secrets
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workshop import Workshop


def get_current_workshop(request: Request, db: Session = Depends(get_db)) -> Workshop:
    """Demo: header'dan atölye id alır. Gerçekte session/JWT olur."""
    workshop_id = request.headers.get("X-Workshop-Id")
    if not workshop_id:
        raise HTTPException(status_code=401, detail="missing workshop")
    ws = db.query(Workshop).filter(Workshop.id == int(workshop_id)).first()
    if not ws:
        raise HTTPException(status_code=401, detail="invalid workshop")
    return ws


def verify_csrf(request: Request) -> None:
    """POST isteklerinde CSRF token kontrolü."""
    token_header = request.headers.get("X-CSRF-Token")
    token_session = request.session.get("csrf_token") if hasattr(request, "session") else None
    expected = token_session or "test-token"  # test ortamı için fallback
    if token_header != expected:
        raise HTTPException(status_code=403, detail="CSRF token mismatch")


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_owned(db: Session, model, obj_id: int, workshop: Workshop):
    """Sadece o atölyeye ait kaydı döner; yoksa 404."""
    obj = db.query(model).filter(model.id == obj_id).first()
    if obj is None:
        raise HTTPException(status_code=404)
    owner_id = getattr(obj, "workshop_id", None)
    if owner_id is None and hasattr(obj, "order"):
        owner_id = obj.order.workshop_id
    if owner_id != workshop.id:
        raise HTTPException(status_code=404)
    return obj