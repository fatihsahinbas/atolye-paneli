"""Ödeme sağlayıcı webhook'u (iyzico/PayTR adaptörü buraya bağlanacak).  Sahip: Hasan

Güvenlik (Checklist #17):
  1. İmza: HMAC-SHA256(secret, f"{timestamp}.{body}") — timing-safe karşılaştırma
  2. Zaman damgası ±5 dk dışındaysa red (replay)
  3. event_id tekil — aynı olay iki kez işlenmez (idempotency)
"""
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import hmac_sha256, safe_equals
from app.modules.payments.models import ProcessedWebhook

router = APIRouter(prefix="/webhooks", tags=["payments"])
log = logging.getLogger("atolye.payments")

MAX_BODY = 64 * 1024


def verify_signature(
    secret: str, body: bytes, timestamp: str, signature: str, tolerance: int, now: float | None = None
) -> bool:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs((now or time.time()) - ts) > tolerance:
        return False
    expected = hmac_sha256(secret, f"{ts}.".encode() + body)
    return safe_equals(expected, signature or "")


@router.post("/odeme")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    s = request.app.state.settings
    if not s.payment_webhook_secret:
        raise HTTPException(503, "Webhook devre dışı")
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(413)
    ok = verify_signature(
        s.payment_webhook_secret, body,
        request.headers.get("X-Timestamp", ""), request.headers.get("X-Signature", ""),
        s.webhook_tolerance_sec,
    )
    if not ok:
        log.warning("Geçersiz webhook imzası")
        raise HTTPException(401)
    try:
        payload = json.loads(body)
        event_id = str(payload["event_id"])[:100]
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400) from None
    if db.scalar(select(ProcessedWebhook.id).where(ProcessedWebhook.event_id == event_id)):
        return {"status": "duplicate"}
    db.add(ProcessedWebhook(provider="generic", event_id=event_id, payload=body.decode("utf-8", "replace")))
    db.commit()
    # TODO(Hasan): payload["type"] == "subscription.paid" → atölye aboneliğini uzat
    return {"status": "ok"}
