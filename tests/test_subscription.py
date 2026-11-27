"""H4 PROJE 1 · Abonelik domain kuralları (saf Python)."""
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.subscription import add_months, extend, is_active

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)


def test_add_months_clamps_to_month_end():
    assert add_months(datetime(2027, 1, 31, tzinfo=UTC), 1).date().isoformat() == "2027-02-28"
    assert add_months(datetime(2028, 1, 31, tzinfo=UTC), 1).date().isoformat() == "2028-02-29"
    assert add_months(datetime(2026, 11, 30, tzinfo=UTC), 3).date().isoformat() == "2027-02-28"


def test_extend_from_now_when_expired():
    assert extend(NOW - timedelta(days=3), NOW, 1) == add_months(NOW, 1)
    assert extend(None, NOW, 1) == add_months(NOW, 1)


def test_extend_from_end_when_still_valid():
    end = NOW + timedelta(days=10)
    assert extend(end, NOW, 1) == add_months(end, 1)


def test_naive_datetime_raises():
    with pytest.raises(TypeError):
        extend(datetime(2026, 12, 1), NOW, 1)


def test_is_active():
    assert is_active(NOW + timedelta(days=1), NOW, False)
    assert not is_active(NOW - timedelta(seconds=1), NOW, False)
    assert not is_active(None, NOW, False)
    assert is_active(None, NOW, True)
