"""Atölye ayarları: ad + telefon.  Sahip: Seher

Workshop kiracının kendisidir: kayıt `scoped()` ile değil, oturumdaki kullanıcının
`workshop_id`'si ile bulunur. URL'de atölye id'si yoktur, başka atölyeye erişilemez.
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import csrf_protect, require_owner
from app.core.templating import render
from app.modules.auth.models import User
from app.modules.auth.schemas import first_error
from app.modules.workshop.models import Workshop
from app.modules.workshop.schemas import WorkshopSettingsIn

router = APIRouter(prefix="/atolye", tags=["workshop"])


def _page(request: Request, ws: Workshop, status_code: int = 200, **extra):
    form = extra.pop("form", {"name": ws.name, "phone": ws.phone or ""})
    return render(request, "workshop/settings.html", {"workshop": ws, "form": form, **extra}, status_code=status_code)


@router.get("/ayarlar")
def settings_form(
    request: Request, kaydedildi: int = 0, db: Session = Depends(get_db), user: User = Depends(require_owner)
):
    ws = db.get(Workshop, user.workshop_id)
    return _page(request, ws, saved=bool(kaydedildi))


@router.post("/ayarlar", dependencies=[Depends(csrf_protect)])
def save_settings(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_owner),
    name: str = Form(""),
    phone: str = Form(""),
):
    ws = db.get(Workshop, user.workshop_id)
    try:
        data = WorkshopSettingsIn(name=name, phone=phone or None)
    except ValidationError as e:
        return _page(request, ws, status_code=422, error=first_error(e), form={"name": name, "phone": phone})
    ws.name = data.name
    ws.phone = data.phone
    db.commit()
    return RedirectResponse("/atolye/ayarlar?kaydedildi=1", status_code=303)
