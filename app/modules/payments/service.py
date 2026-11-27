"""Abonelik ödemesi iş kuralları.  Sahip: Hasan (H4)"""
import logging
import secrets
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.deps import as_aware
from app.domain.plans import Plan
from app.domain.subscription import extend
from app.modules.auth.models import User
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.providers import CheckoutRequest, CheckoutStart, PaymentProvider, PaymentResult
from app.modules.workshop.models import Workshop

log = logging.getLogger("atolye.payments")


def new_merchant_oid() -> str:
    return "AP" + secrets.token_hex(12).upper()  # yalnız harf + rakam (PayTR şartı)


def start_checkout(
    db: Session, user: User, plan: Plan, provider: PaymentProvider, buyer_ip: str, base_url: str, months: int = 1
) -> tuple[Payment, CheckoutStart]:
    if not plan.is_paid:
        raise ValueError("Bu paket için ödeme alınmaz")
    p = Payment(
        workshop_id=user.workshop_id, merchant_oid=new_merchant_oid(), provider=provider.name,
        plan_code=plan.code, months=months, amount=(plan.monthly_price * months).quantize(Decimal("0.01")),
    )
    db.add(p)
    db.flush()
    base = base_url.rstrip("/")
    start = provider.start(CheckoutRequest(
        merchant_oid=p.merchant_oid, amount=p.amount, description=f"{plan.name} paketi · {months} ay",
        buyer_email=user.email, buyer_name=user.full_name, buyer_ip=buyer_ip,
        callback_url=f"{base}/odeme/iyzico/donus",
        ok_url=f"{base}/abonelik?sonuc=ok", fail_url=f"{base}/abonelik?sonuc=hata",
    ))
    p.provider_ref = start.provider_ref or None
    db.commit()
    return p, start


def apply_result(db: Session, result: PaymentResult) -> Payment | None:
    """Sağlayıcı sonucunu uygular. İdempotent: PAID kayıt tekrar işlenmez. Tek commit."""
    p = db.scalar(select(Payment).where(Payment.merchant_oid == result.merchant_oid).with_for_update())
    if p is None:
        return None
    if p.status == PaymentStatus.PAID:
        return p  # aynı bildirim ikinci kez geldi
    if not result.success:
        p.status = PaymentStatus.FAILED
    elif result.amount != p.amount:
        log.warning("Ödeme tutarı uyuşmuyor (oid=%s)", p.merchant_oid)
        p.status = PaymentStatus.FAILED
    else:
        ws = db.get(Workshop, p.workshop_id)
        now = utcnow()
        current = as_aware(ws.subscription_ends_at) if ws.subscription_ends_at else None
        ws.subscription_ends_at = extend(current, now, p.months)
        ws.plan_code = p.plan_code
        p.status, p.paid_at = PaymentStatus.PAID, now
    db.commit()
    return p
