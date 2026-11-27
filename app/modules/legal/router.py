"""KVKK aydınlatma metni /kvkk (giriş gerektirmez).  Sahip: Hasan (H3 PROJE 4)"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templating import render
from app.modules.workshop.models import Workshop

router = APIRouter(tags=["legal"])

KVKK_UPDATED = "27.11.2026"


@router.get("/kvkk")
def kvkk(request: Request, atolye: str = Query("", max_length=60), db: Session = Depends(get_db)):
    """?atolye=<slug> verilirse [ATÖLYE ADI] yerine gerçek atölye adı yazılır."""
    ws = db.scalar(select(Workshop).where(Workshop.slug == atolye)) if atolye else None
    return render(
        request,
        "public/kvkk.html",
        {"workshop_name": ws.name if ws else "[ATÖLYE ADI]", "updated": KVKK_UPDATED},
    )
