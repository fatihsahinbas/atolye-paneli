"""Abonelik süresi kuralları.  Sahip: Hasan (H4 PROJE 1)

Saf Python. DB'den gelen tarihleri buraya vermeden önce as_aware() ile sar (SQLite tz saklamaz).
"""
import calendar
from datetime import datetime

TRIAL_DAYS = 14


def add_months(dt: datetime, n: int) -> datetime:
    """Ay sonuna kırpar: 31 Ocak + 1 ay → 28/29 Şubat."""
    if n < 0:
        raise ValueError("Ay sayısı negatif olamaz")
    month_index = dt.month - 1 + n
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def extend(current_end: datetime | None, now: datetime, months: int) -> datetime:
    """Hâlâ geçerliyse bitiş tarihinden, bitmişse şimdiden uzatır (erken ödeyen gün kaybetmez)."""
    if now.tzinfo is None or (current_end is not None and current_end.tzinfo is None):
        raise TypeError("Tarihler saat dilimli olmalı (as_aware)")
    base = current_end if current_end and current_end > now else now
    return add_months(base, months)


def is_active(ends_at: datetime | None, now: datetime, is_pilot: bool) -> bool:
    if is_pilot:
        return True
    return ends_at is not None and ends_at > now
