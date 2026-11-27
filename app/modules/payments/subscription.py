"""Abonelik ekranı ve ödeme dönüş uçları.  Sahip: Hasan (H4 PROJE 1)

/abonelik ve /abonelik/baslat yalnız OWNER. Dönüş uçları sağlayıcıdan gelir:
  - iyzico dönüşü tarayıcıdan POST'tur; SameSite=Lax çerez gelmez → current_user YOK, token ile bulunur
  - PayTR bildirimi sunucudan gelir; cevap düz metin "OK"
"""
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db, utcnow
from app.core.deps import as_aware, csrf_protect, require_owner
from app.core.templating import render
from app.core.tenancy import get_owned, scoped
from app.domain.plans import get_plan, paid_plans
from app.domain.subscription import is_active
from app.modules.auth.models import User
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.providers import (
    FakeProvider,
    InvalidSignature,
    IyzicoProvider,
    PaymentResult,
    PaytrProvider,
    ProviderError,
)
from app.modules.payments.service import apply_result, start_checkout
from app.modules.workshop.models import Workshop

router = APIRouter(tags=["subscription"])
log = logging.getLogger("atolye.payments")

RESULT_MESSAGES = {
    "ok": "Ödeme alındı, aboneliğiniz uzatıldı.",
    "hata": "Ödeme tamamlanamadı. Kartınızdan para çekilmedi.",
    "bekliyor": "Ödeme sonucu henüz gelmedi. Birazdan 'Durumu kontrol et' ile tekrar bakın.",
}


def _provider(request: Request):
    return request.app.state.payment_provider


def _base_url(request: Request) -> str:
    return request.app.state.settings.public_base_url or str(request.base_url)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd else "") or (request.client.host if request.client else "127.0.0.1")


def _page(request: Request, db: Session, user: User, **extra):
    ws = db.get(Workshop, user.workshop_id)
    ends = as_aware(ws.subscription_ends_at) if ws.subscription_ends_at else None
    payments = db.scalars(scoped(Payment, user).order_by(Payment.id.desc()).limit(10)).all()
    return render(request, "subscription/index.html", {
        "workshop": ws, "ends_at": ends, "active": is_active(ends, utcnow(), ws.is_pilot),
        "current_plan": get_plan(ws.plan_code) if ws.plan_code else None,
        "plans": paid_plans(), "payments": payments, "provider": _provider(request).name,
        "result": RESULT_MESSAGES.get(request.query_params.get("sonuc", "")), **extra,
    })


@router.get("/abonelik")
def subscription_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    return _page(request, db, user)


@router.post("/abonelik/baslat", dependencies=[Depends(csrf_protect)])
def subscription_start(
    request: Request,
    plan_code: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_owner),
):
    ws = db.get(Workshop, user.workshop_id)
    if ws.is_pilot:
        raise HTTPException(400, "Pilot atölyeler ödeme yapmaz")
    try:
        plan = get_plan(plan_code)
        payment, start = start_checkout(db, user, plan, _provider(request), _client_ip(request), _base_url(request))
    except ValueError:
        raise HTTPException(400, "Geçersiz paket") from None
    except ProviderError:
        db.rollback()
        log.warning("Ödeme başlatılamadı (sağlayıcı=%s)", _provider(request).name)
        return _page(request, db, user, error="Ödeme sağlayıcısına ulaşılamadı, lütfen tekrar deneyin.")
    if start.iframe_url:
        return render(request, "subscription/paytr.html", {"iframe_url": start.iframe_url, "payment": payment})
    return RedirectResponse(start.redirect_url, status_code=303)


@router.post("/abonelik/kontrol/{payment_id}", dependencies=[Depends(csrf_protect)])
def subscription_check(
    request: Request, payment_id: int, db: Session = Depends(get_db), user: User = Depends(require_owner)
):
    """PENDING kalmış iyzico ödemesini sağlayıcıya tekrar sorar."""
    p = get_owned(db, Payment, payment_id, user)
    provider = _provider(request)
    if p.status == PaymentStatus.PENDING and isinstance(provider, IyzicoProvider) and p.provider_ref:
        apply_result(db, provider.retrieve(p.provider_ref))
    return RedirectResponse("/abonelik", status_code=303)


# --- Sağlayıcı dönüşleri ---------------------------------------------------------


@router.post("/odeme/iyzico/donus")
def iyzico_return(request: Request, token: str = Form(..., max_length=200), db: Session = Depends(get_db)):
    """Çerezsiz gelir. CSRF formu yok; güvenliği retrieve sorgusu sağlar."""
    provider = _provider(request)
    if not isinstance(provider, IyzicoProvider):
        raise HTTPException(404)
    p = db.scalar(select(Payment).where(Payment.provider_ref == token))
    if p is None:
        return RedirectResponse("/abonelik?sonuc=hata", status_code=303)
    result = provider.retrieve(token)
    result = PaymentResult(p.merchant_oid, result.success, result.amount, token)  # oid bizim kaydımızdan
    paid = apply_result(db, result)
    ok = paid is not None and paid.status == PaymentStatus.PAID
    return RedirectResponse(f"/abonelik?sonuc={'ok' if ok else 'hata'}", status_code=303)


@router.post("/odeme/paytr/bildirim")
async def paytr_notification(request: Request, db: Session = Depends(get_db)):
    provider = _provider(request)
    if not isinstance(provider, PaytrProvider):
        raise HTTPException(404)
    form = {k: str(v) for k, v in (await request.form()).items()}
    try:
        result = provider.verify_notification(form)
    except InvalidSignature:
        log.warning("PayTR bildirimi: geçersiz imza")
        raise HTTPException(400, "bad hash") from None
    apply_result(db, result)
    return PlainTextResponse("OK")  # başka hiçbir şey yazılmaz, yoksa PayTR tekrar dener


# --- Fake sağlayıcı: anahtarsız demo ödeme sayfası --------------------------------


def _fake_payment(request: Request, db: Session, user: User, oid: str) -> Payment:
    if not isinstance(_provider(request), FakeProvider):
        raise HTTPException(404)
    p = db.scalar(scoped(Payment, user).where(Payment.merchant_oid == oid[:64]))
    if p is None:
        raise HTTPException(404)
    return p


@router.get("/odeme/test/{oid}")
def fake_checkout(request: Request, oid: str, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    p = _fake_payment(request, db, user, oid)
    return render(request, "subscription/fake.html", {"payment": p, "plan": get_plan(p.plan_code)})


@router.post("/odeme/test/{oid}", dependencies=[Depends(csrf_protect)])
def fake_checkout_submit(
    request: Request,
    oid: str,
    sonuc: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_owner),
):
    p = _fake_payment(request, db, user, oid)
    paid = apply_result(db, PaymentResult(p.merchant_oid, sonuc == "ok", p.amount))
    ok = paid is not None and paid.status == PaymentStatus.PAID
    return RedirectResponse(f"/abonelik?sonuc={'ok' if ok else 'hata'}", status_code=303)
