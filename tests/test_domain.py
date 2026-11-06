from decimal import Decimal

import pytest

from app.core.logging import mask
from app.domain.order_status import InvalidTransition, allowed_next, ensure_transition, is_terminal
from app.domain.order_status import OrderStatus as S
from app.domain.pricing import PricingError, price_fixed, price_gold


class TestOrderStatus:
    def test_happy_path(self):
        path = [S.RECEIVED, S.DESIGN_APPROVAL, S.IN_PRODUCTION, S.QUALITY_CHECK, S.SHIPPED, S.DELIVERED]
        for a, b in zip(path, path[1:], strict=False):
            ensure_transition(a, b)

    def test_rework_from_quality(self):
        ensure_transition(S.QUALITY_CHECK, S.IN_PRODUCTION)

    @pytest.mark.parametrize("a,b", [(S.RECEIVED, S.DELIVERED), (S.SHIPPED, S.CANCELLED), (S.DELIVERED, S.RECEIVED)])
    def test_invalid(self, a, b):
        with pytest.raises(InvalidTransition):
            ensure_transition(a, b)

    def test_terminal(self):
        assert is_terminal(S.DELIVERED) and is_terminal(S.CANCELLED)
        assert allowed_next(S.DELIVERED) == []


class TestPricing:
    def test_gold_example(self):
        # 5 gr, 22 ayar (916), işçilik 30 milyem, has 3000 TL → 14.190,00 net
        bd = price_gold(Decimal("5"), 916, 30, Decimal("3000"), vat_rate=Decimal("20"))
        assert bd.material == Decimal("13740.00")
        assert bd.labor == Decimal("450.00")
        assert bd.net == Decimal("14190.00")
        assert bd.vat == Decimal("2838.00")
        assert bd.gross == Decimal("17028.00")

    def test_fixed_with_extra_and_qty(self):
        bd = price_fixed(Decimal("1000"), Decimal("150"), Decimal("20")).times(2)
        assert bd.net == Decimal("2300.00") and bd.gross == Decimal("2760.00")

    def test_gold_requires_price(self):
        with pytest.raises(PricingError):
            price_gold(Decimal("5"), 916, 30, None)

    def test_rounding_half_up(self):
        assert price_fixed(Decimal("0.125"), vat_rate=Decimal(0)).net == Decimal("0.13")


def test_log_masking():
    out = mask("musteri ali.veli@ornek.com tel 0532 111 22 33 token=abc123")
    assert "ali.veli" not in out and "111 22" not in out and "abc123" not in out
