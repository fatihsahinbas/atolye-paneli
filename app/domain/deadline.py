"""Termin hesabı ve gecikme durumu.  Sahip: Çınar (H4 PROJE 4)

Saf Python. "Gecikti" DB'ye yazılmaz; her gösterimde hesaplanır.
"""
from datetime import date, timedelta
from typing import Literal

from app.domain.order_status import OrderStatus

DeadlineState = Literal["none", "ok", "soon", "late"]
SOON_DAYS = 2

# Resmî tatiller (2429 sayılı Kanun). Dini bayram tarihleri her yıl değişir.
# Kaynak: Diyanet İşleri Başkanlığı dini günler takvimi (2026, 2027).
# Arife günleri yarım gün olduğu için iş günü sayılır.
_FIXED = [(1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 29)]
_RELIGIOUS = [
    date(2026, 3, 20), date(2026, 3, 21), date(2026, 3, 22),                       # Ramazan Bayramı
    date(2026, 5, 27), date(2026, 5, 28), date(2026, 5, 29), date(2026, 5, 30),    # Kurban Bayramı
    date(2027, 3, 9), date(2027, 3, 10), date(2027, 3, 11),                        # Ramazan Bayramı
    date(2027, 5, 16), date(2027, 5, 17), date(2027, 5, 18), date(2027, 5, 19),    # Kurban Bayramı
]
TR_HOLIDAYS_2026_2027: frozenset[date] = frozenset(
    [date(y, m, d) for y in (2026, 2027) for m, d in _FIXED] + _RELIGIOUS
)

_CLOSED = {OrderStatus.DELIVERED, OrderStatus.CANCELLED}


def is_business_day(d: date, holidays: frozenset[date] = TR_HOLIDAYS_2026_2027) -> bool:
    return d.weekday() < 5 and d not in holidays


def add_business_days(start: date, days: int, holidays: frozenset[date] = TR_HOLIDAYS_2026_2027) -> date:
    """start'tan sonra `days` iş günü ileri. Hafta sonu ve tatiller atlanır."""
    if days < 0:
        raise ValueError("Gün sayısı negatif olamaz")
    d = start
    left = days
    while left:
        d += timedelta(days=1)
        if is_business_day(d, holidays):
            left -= 1
    return d


def suggest_due_date(
    today: date, production_days: list[int | None], holidays: frozenset[date] = TR_HOLIDAYS_2026_2027
) -> date | None:
    """Kalemlerdeki en uzun üretim süresi. Süresi girilmemiş ürünler sayılmaz; hiçbiri yoksa None."""
    known = [d for d in production_days if d is not None]
    if not known:
        return None
    return add_business_days(today, max(known), holidays)


def deadline_state(due: date | None, today: date, status: OrderStatus) -> DeadlineState:
    if due is None:
        return "none"
    if status in _CLOSED:
        return "ok"
    if due < today:
        return "late"
    if (due - today).days <= SOON_DAYS:
        return "soon"
    return "ok"
