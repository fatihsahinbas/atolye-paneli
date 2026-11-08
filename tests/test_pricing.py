from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.pricing import PricingError, PricingType, price_gold, price_gold_cost_plus
from app.modules.catalog.router import ProductIn


def test_gold_necklace_with_margin():
    p = price_gold(Decimal(10), 585, 130, Decimal(3000), margin_percent=Decimal(15))
    assert p.material == Decimal("17550.00")
    assert p.labor == Decimal("3900.00")
    assert p.margin == Decimal("3217.50")
    assert p.net == Decimal("24667.50")
    assert p.vat == Decimal("4933.50")
    assert p.gross == Decimal("29601.00")


def test_cost_plus_adana_burma():
    p = price_gold_cost_plus(Decimal(50), Decimal(921), Decimal(30), Decimal(3000))
    assert p.material == Decimal("138150.00")
    assert p.margin == Decimal("1500.00")
    assert p.net == Decimal("139650.00")
    assert p.vat == Decimal("27930.00")
    assert p.gross == Decimal("167580.00")


def test_cost_plus_requires_has_price():
    with pytest.raises(PricingError):
        price_gold_cost_plus(Decimal(50), Decimal(921), Decimal(30), None)


def test_cost_plus_rejects_negative_margin():
    with pytest.raises(PricingError):
        price_gold_cost_plus(Decimal(50), Decimal(921), Decimal(-1), Decimal(3000))


# --- Claude ekledi: ürün formu bağlanana kadar koruma -----------------------


def test_margin_is_multiplied_by_quantity():
    p = price_gold(Decimal(10), 585, 130, Decimal(3000), margin_percent=Decimal(15)).times(2)
    assert p.margin == Decimal("6435.00") and p.net == Decimal("49335.00")


def test_product_form_rejects_cost_plus_until_wired():
    # Katalog servisi GOLD_COST_PLUS'ı henüz bilmiyor; kabul edilirse ürün 0 TL'ye düşer.
    with pytest.raises(ValidationError, match="henüz desteklenmiyor"):
        ProductIn(name="Adana burma", pricing_type=PricingType.GOLD_COST_PLUS)
