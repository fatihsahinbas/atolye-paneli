"""Fiyat motoru.  Sahip: Hayrettin

Üç fiyat tipi:
  FIXED          : sabit fiyat (filografi, el sanatı)
  GOLD           : kolye/künye — gram × (ayar milyemi + işçilik milyemi) × has fiyat,
                   üzerine kâr yüzdesi
  GOLD_COST_PLUS : adana burması/bilezik — gram × toptancı maliyet milyemi × has fiyat,
                   üzerine gram başı sabit TL kâr

Örnek GOLD: 10 gr 14 ayar (585) kolye, işçilik 130 milyem, has 3.000 TL, kâr %15
       malzeme 17.550 + işçilik 3.900 + kâr 3.217,50 = 24.667,50 TL (KDV hariç)
Örnek GOLD_COST_PLUS: 50 gr adana burması, maliyet 921 milyem, has 3.000 TL, kâr 30 TL/gr
       maliyet 138.150 + kâr 1.500 = 139.650,00 TL (KDV hariç)

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
    GOLD_COST_PLUS = "GOLD_COST_PLUS"


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
    margin: Decimal = Decimal(0)  # kâr payı

    def times(self, qty: int) -> "PriceBreakdown":
        q = Decimal(qty)
        fields = (self.material, self.labor, self.extra, self.net, self.vat, self.gross, self.margin)
        return PriceBreakdown(*(money(v * q) for v in fields))


def _finish(
    material: Decimal,
    labor: Decimal,
    extra: Decimal,
    vat_rate: Decimal,
    margin: Decimal = Decimal(0),
) -> PriceBreakdown:
    net = money(material + labor + margin + extra)
    vat = money(net * vat_rate / Decimal(100))
    return PriceBreakdown(
        money(material), money(labor), money(extra), net, vat, money(net + vat), money(margin)
    )


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
    margin_percent: Decimal = Decimal(0),
) -> PriceBreakdown:
    if has_price_per_gram is None or has_price_per_gram <= 0:
        raise PricingError("Güncel has altın fiyatı girilmemiş")
    if weight_g <= 0:
        raise PricingError("Gram 0'dan büyük olmalı")
    if not 0 < purity_milyem <= 1000 or not 0 <= labor_milyem <= 500:
        raise PricingError("Milyem değerleri geçersiz")
    if margin_percent < 0:
        raise PricingError("Kâr oranı negatif olamaz")
    material = weight_g * Decimal(purity_milyem) / MILYEM * has_price_per_gram
    labor = weight_g * Decimal(labor_milyem) / MILYEM * has_price_per_gram
    margin = (material + labor) * margin_percent / Decimal(100)
    return _finish(material, labor, extra, vat_rate, margin)


def price_gold_cost_plus(
    weight_g: Decimal,
    cost_milyem: Decimal,
    margin_tl_per_gram: Decimal,
    has_price_per_gram: Decimal | None,
    extra: Decimal = Decimal(0),
    vat_rate: Decimal = Decimal(20),
) -> PriceBreakdown:
    if has_price_per_gram is None or has_price_per_gram <= 0:
        raise PricingError("Güncel has altın fiyatı girilmemiş")
    if weight_g <= 0:
        raise PricingError("Gram 0'dan büyük olmalı")
    if not 0 < cost_milyem <= 1000:
        raise PricingError("Milyem değeri geçersiz")
    if margin_tl_per_gram < 0 or extra < 0:
        raise PricingError("Fiyat negatif olamaz")
    material = weight_g * cost_milyem / MILYEM * has_price_per_gram  # maliyet
    margin = weight_g * margin_tl_per_gram
    return _finish(material, Decimal(0), extra, vat_rate, margin)
