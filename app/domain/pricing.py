"""Fiyat motoru.  Sahip: Hayrettin

İki fiyat tipi:
  FIXED : sabit fiyat (filografi, el sanatı)
  GOLD  : kuyumcu — gram × (ayar milyemi + işçilik milyemi) × has altın gram fiyatı

Örnek: 5 gr 22 ayar (916) bilezik, işçilik 30 milyem, has 3.000 TL
       5 × (0.916 + 0.030) × 3000 = 14.190,00 TL (KDV hariç)

Tüm para hesapları Decimal ile yapılır; float YASAK.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

TWO = Decimal("0.01")
MILYEM = Decimal("1000")

# Yaygın ayar → milyem karşılıkları
PURITY_MILYEM: dict[str, int] = {"8K": 333, "14K": 585, "18K": 750, "22K": 916, "24K": 995}


class PricingType(StrEnum):
    FIXED = "FIXED"
    GOLD = "GOLD"


class PricingError(ValueError):
    pass


def money(value: Decimal) -> Decimal:
    return value.quantize(TWO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PriceBreakdown:
    material: Decimal  # malzeme (altın değeri veya sabit fiyat)
    labor: Decimal  # işçilik
    extra: Decimal  # taş, kutu, gravür vb.
    net: Decimal
    vat: Decimal
    gross: Decimal

    def times(self, qty: int) -> "PriceBreakdown":
        q = Decimal(qty)
        fields = (self.material, self.labor, self.extra, self.net, self.vat, self.gross)
        return PriceBreakdown(*(money(v * q) for v in fields))


def _finish(material: Decimal, labor: Decimal, extra: Decimal, vat_rate: Decimal) -> PriceBreakdown:
    net = money(material + labor + extra)
    vat = money(net * vat_rate / Decimal(100))
    return PriceBreakdown(money(material), money(labor), money(extra), net, vat, money(net + vat))


def price_fixed(base_price: Decimal, extra: Decimal = Decimal(0), vat_rate: Decimal = Decimal(20)) -> PriceBreakdown:
    if base_price < 0 or extra < 0:
        raise PricingError("Fiyat negatif olamaz")
    return _finish(base_price, Decimal(0), extra, vat_rate)


def price_gold(
    weight_g: Decimal,
    purity_milyem: int,
    labor_milyem: int,
    has_price_per_gram: Decimal | None,
    extra: Decimal = Decimal(0),
    vat_rate: Decimal = Decimal(20),
) -> PriceBreakdown:
    if has_price_per_gram is None or has_price_per_gram <= 0:
        raise PricingError("Güncel has altın fiyatı girilmemiş")
    if weight_g <= 0:
        raise PricingError("Gram 0'dan büyük olmalı")
    if not 0 < purity_milyem <= 1000 or not 0 <= labor_milyem <= 500:
        raise PricingError("Milyem değerleri geçersiz")
    material = weight_g * Decimal(purity_milyem) / MILYEM * has_price_per_gram
    labor = weight_g * Decimal(labor_milyem) / MILYEM * has_price_per_gram
    return _finish(material, labor, extra, vat_rate)
