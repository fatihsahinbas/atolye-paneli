import pytest

from app.domain.plans import (
    PILOT_DISCOUNT_PERCENT,
    can_create_order,
    effective_monthly_price,
    get_plan,
    list_paid_plans,
    list_plans,
    remaining_orders,
)
from tests.conftest import make_client


def test_plans_structure_and_two_paid_tiers():
    all_plans = list_plans()
    paid = list_paid_plans()
    assert len(all_plans) == 3
    assert len(paid) == 2
    assert get_plan("baslangic").is_paid is False
    assert all(p.is_paid and p.monthly_price_tl > 0 for p in paid)


def test_pilot_discount_calculation():
    atolye = get_plan("atolye")
    assert PILOT_DISCOUNT_PERCENT == 50
    assert atolye.pilot_price_tl() == 475
    assert effective_monthly_price("atolye", is_pilot=False) == 950
    assert effective_monthly_price("atolye", is_pilot=True) == 475
    assert effective_monthly_price("baslangic", is_pilot=True) == 0


def test_monthly_order_limit_and_remaining():
    free_limit = get_plan("baslangic").monthly_order_limit
    assert free_limit == 20
    assert can_create_order("baslangic", 19) is True
    assert can_create_order("baslangic", 20) is False
    assert remaining_orders("baslangic", 14) == 6
    assert remaining_orders("baslangic", 25) == 0

    atolye_limit = get_plan("atolye").monthly_order_limit
    assert atolye_limit == 150
    assert can_create_order("atolye", 149) is True
    assert can_create_order("atolye", 150) is False

    assert can_create_order("usta_pro", 50_000) is True
    assert remaining_orders("usta_pro", 50_000) is None


def test_negative_order_count_raises():
    with pytest.raises(ValueError):
        can_create_order("baslangic", -1)
    with pytest.raises(ValueError):
        remaining_orders("baslangic", -1)


def test_public_pricing_page_renders_without_login(app):
    client = make_client(app)
    res = client.get("/fiyatlar")
    assert res.status_code == 200
    html = res.text
    assert "Başlangıç" in html
    assert "Atölye" in html
    assert "Usta Pro" in html
    assert "%50 Pilot İndirimi" in html
    assert "475 ₺" in html
    assert "975 ₺" in html
