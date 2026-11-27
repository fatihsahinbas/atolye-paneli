from datetime import date

import pytest

from app.domain.deadline import TR_HOLIDAYS_2026_2027, add_business_days, deadline_state, suggest_due_date
from app.domain.order_status import OrderStatus

TODAY = date(2026, 11, 27)  # Cuma


def test_friday_plus_one_is_monday():
    assert add_business_days(date(2026, 11, 27), 1) == date(2026, 11, 30)


def test_republic_day_is_skipped():
    assert date(2026, 10, 29) in TR_HOLIDAYS_2026_2027
    assert add_business_days(date(2026, 10, 28), 1) == date(2026, 10, 30)


def test_bayram_is_skipped():
    # 2027 Ramazan Bayramı 9–11 Mart (Salı–Perşembe)
    assert add_business_days(date(2027, 3, 8), 1) == date(2027, 3, 12)


def test_negative_days_raises():
    with pytest.raises(ValueError):
        add_business_days(TODAY, -1)


def test_suggestion_uses_longest_known_duration():
    assert suggest_due_date(TODAY, [2, None, 5]) == add_business_days(TODAY, 5)
    assert suggest_due_date(TODAY, [None, None]) is None
    assert suggest_due_date(TODAY, []) is None


@pytest.mark.parametrize(
    ("due", "status", "expected"),
    [
        (None, OrderStatus.RECEIVED, "none"),
        (date(2026, 11, 29), OrderStatus.IN_PRODUCTION, "soon"),
        (date(2026, 11, 27), OrderStatus.IN_PRODUCTION, "soon"),
        (date(2026, 11, 26), OrderStatus.IN_PRODUCTION, "late"),
        (date(2026, 12, 10), OrderStatus.RECEIVED, "ok"),
        (date(2026, 11, 1), OrderStatus.DELIVERED, "ok"),
        (date(2026, 11, 1), OrderStatus.CANCELLED, "ok"),
    ],
)
def test_deadline_state(due, status, expected):
    assert deadline_state(due, TODAY, status) == expected


# --- HTTP: pano ve termin önerisi -------------------------------------------------
from datetime import timedelta  # noqa: E402

from app.domain.deadline import add_business_days as _abd  # noqa: E402
from app.modules.catalog.models import Product  # noqa: E402
from app.modules.orders.models import Order  # noqa: E402
from tests.conftest import csrf, make_client, register, seed_order  # noqa: E402


def _set_due(app, oid, due):
    with app.state.SessionLocal() as db:
        db.get(Order, oid).due_date = due
        db.commit()


def test_board_marks_late_and_soon(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    late, soon, ok = seed_order(c), seed_order(c), seed_order(c)
    today = date.today()
    _set_due(app, late, today - timedelta(days=1))
    _set_due(app, soon, today + timedelta(days=2))
    _set_due(app, ok, today + timedelta(days=20))
    html = c.get("/").text
    assert html.count("ticket--late") == 1
    assert html.count("ticket--soon") == 1


def test_board_hides_other_workshop(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@ornek.com")
    register(b, "atolye-b", "b@ornek.com")
    oid = seed_order(a)
    assert f'data-order-id="{oid}"' not in b.get("/").text


def test_due_date_suggestion_endpoint(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    t = csrf(c, "/urunler")
    c.post("/urunler", data={"csrf_token": t, "name": "Kolye", "pricing_type": "FIXED", "base_price": "10",
                             "avg_production_days": "3"})
    c.post("/urunler", data={"csrf_token": t, "name": "Kutu", "pricing_type": "FIXED", "base_price": "10"})
    with app.state.SessionLocal() as db:
        assert db.get(Product, 1).avg_production_days == 3
        assert db.get(Product, 2).avg_production_days is None
    r = c.get("/siparisler/termin-onerisi?urun=1&urun=2")
    assert r.json() == {"due_date": _abd(date.today(), 3).isoformat()}
    assert c.get("/siparisler/termin-onerisi?urun=2").json() == {"due_date": None}

    b = make_client(app)
    register(b, "atolye-b", "b@ornek.com")
    assert b.get("/siparisler/termin-onerisi?urun=1").status_code == 404
