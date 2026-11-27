"""Jinja2 şablonları. Autoescape açık — |safe filtresi bu projede yasak (Checklist #16)."""
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.domain.order_status import LABELS

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")
assert templates.env.autoescape, "autoescape kapalı olamaz"


def tl(value: Decimal | int | float | None) -> str:
    """14190.5 → '14.190,50 ₺'"""
    if value is None:
        return "—"
    s = f"{Decimal(value):,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"


TR = ZoneInfo("Europe/Istanbul")


def yerel(dt: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
    """DB'deki UTC zamanı Türkiye saatine çevirir."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(TR).strftime(fmt)


templates.env.filters["tl"] = tl
templates.env.filters["yerel"] = yerel
templates.env.globals["STATUS_LABELS"] = LABELS
templates.env.globals["NOTIFY_LABELS"] = {
    "PENDING": "Bekliyor", "SENT": "Gönderildi", "FAILED": "Gönderilemedi",
    "SKIPPED": "Gönderilmedi (izin/iletişim yok)",
}


def _sub_expired(user) -> bool:
    """Üst bant uyarısı: deneme/abonelik süresi doldu (H4: yalnız uyarı, engelleme H5)."""
    from app.domain.subscription import is_active  # döngüsel import olmasın

    ws = getattr(user, "workshop", None)
    if ws is None:
        return False
    ends = ws.subscription_ends_at
    if ends is not None and ends.tzinfo is None:
        ends = ends.replace(tzinfo=UTC)
    return not is_active(ends, datetime.now(UTC), bool(ws.is_pilot))


def render(request: Request, name: str, ctx: dict[str, Any] | None = None, status_code: int = 200):
    sess = getattr(request.state, "session", None)
    user = sess.user if sess else None
    base = {
        "user": user,
        "sub_expired": _sub_expired(user),
        "csrf_token": sess.csrf_token if sess else "",
        "APP_NAME": request.app.state.settings.app_name,
    }
    return templates.TemplateResponse(request, name, {**base, **(ctx or {})}, status_code=status_code)
