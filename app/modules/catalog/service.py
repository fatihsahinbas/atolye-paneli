"""Ürün fiyatlandırma: domain fiyat motorunu ürün + atölye verisiyle çağırır."""
from decimal import Decimal

from app.domain.pricing import PriceBreakdown, PricingType, price_fixed, price_gold
from app.modules.catalog.models import Product
from app.modules.workshop.models import Workshop


def quote(product: Product, workshop: Workshop, qty: int = 1) -> PriceBreakdown:
    """PricingError fırlatabilir (ör. altın fiyatı girilmemiş)."""
    vat = Decimal(workshop.vat_rate)
    extra = Decimal(product.extra_cost or 0)
    if product.pricing_type == PricingType.GOLD:
        unit = price_gold(
            weight_g=Decimal(product.weight_g or 0),
            purity_milyem=product.purity_milyem or 0,
            labor_milyem=product.labor_milyem or 0,
            has_price_per_gram=workshop.gold_price_per_gram,
            extra=extra,
            vat_rate=vat,
        )
    else:
        unit = price_fixed(Decimal(product.base_price or 0), extra, vat)
    return unit.times(qty)
