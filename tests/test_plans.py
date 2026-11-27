from decimal import Decimal

import pytest

from app.domain.plans import (
    PILOT,
    PLANS,
    can_create_order,
    get_plan,
    paid_plans,
    public_plans,
    remaining_orders,
)
from tests.conftest import make_client


def test_two_paid_plans_and_pilot_is_free():
    assert len(paid_plans()) == 2
    assert all(isinstance(p.monthly_price, Decimal) and p.monthly_price > 0 for p in paid_plans())
    assert PILOT.monthly_price == Decimal("0")
    assert PILOT.max_orders_per_month is None
    assert PILOT not in public_plans()
    assert set(PLANS) == {"BASLANGIC", "ATOLYE", "USTA_PRO", "PILOT"}


def test_unknown_code_raises():
    with pytest.raises(ValueError):
        get_plan("YOK")
    with pytest.raises(ValueError):
        get_plan("atolye")  # kodlar büyük harf


@pytest.mark.parametrize(("count", "expected"), [(19, True), (20, False), (21, False)])
def test_can_create_order_limit(count, expected):
    assert can_create_order(get_plan("BASLANGIC"), count) is expected


def test_unlimited_and_remaining():
    assert can_create_order(get_plan("USTA_PRO"), 50_000) is True
    assert remaining_orders(get_plan("USTA_PRO"), 50_000) is None
    assert remaining_orders(get_plan("BASLANGIC"), 14) == 6
    assert remaining_orders(get_plan("BASLANGIC"), 25) == 0


def test_negative_order_count_raises():
    with pytest.raises(ValueError):
        can_create_order(get_plan("BASLANGIC"), -1)
    with pytest.raises(ValueError):
        remaining_orders(get_plan("BASLANGIC"), -1)


def test_public_pricing_page_renders_without_login(app):
    res = make_client(app).get("/fiyatlar")
    assert res.status_code == 200
    html = res.text
    for p in public_plans():
        assert p.name in html
    assert "950,00 ₺" in html
    assert "1.950,00 ₺" in html
    assert "Pilot programındaki atölyeler için demo gününe kadar ücretsiz" in html
    assert "Pilot (ücretsiz)" not in html
    assert "İndirim" not in html
