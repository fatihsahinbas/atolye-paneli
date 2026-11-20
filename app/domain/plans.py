"""Abonelik paketleri, pilot indirimi ve aylık sipariş limit kuralları. Sahip: Hayrettin

Hasan'ın abonelik/ödeme modülü (`Workshop` plan alanı + webhook yenileme)
doğrudan `PLANS`, `get_plan`, `effective_monthly_price` ve `can_create_order` üzerinden bağlanır.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

PILOT_DISCOUNT_PERCENT = 50
PILOT_DURATION_MONTHS = 3


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    tagline: str
    monthly_price_tl: int
    monthly_order_limit: int | None  # None: sınırsız
    max_staff: int | None
    features: tuple[str, ...]
    is_paid: bool = True
    is_popular: bool = False

    def pilot_price_tl(self, discount_percent: int = PILOT_DISCOUNT_PERCENT) -> int:
        if not self.is_paid or self.monthly_price_tl == 0:
            return 0
        raw = Decimal(self.monthly_price_tl) * Decimal(100 - discount_percent) / Decimal(100)
        return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


PLANS: dict[str, Plan] = {
    "baslangic": Plan(
        code="baslangic",
        name="Başlangıç",
        tagline="Yeni kurulan ve küçük ölçekli el emeği atölyeleri",
        monthly_price_tl=0,
        monthly_order_limit=20,
        max_staff=1,
        features=(
            "Aylık 20 siparişe kadar üretim takibi",
            "Temel ürün kataloğu ve atölye vitrini",
            "Müşteri sipariş takip bağlantısı",
        ),
        is_paid=False,
    ),
    "atolye": Plan(
        code="atolye",
        name="Atölye",
        tagline="Kuyumcu ve düzenli sipariş alan büyüyen atölyeler",
        monthly_price_tl=950,
        monthly_order_limit=150,
        max_staff=5,
        features=(
            "Aylık 150 siparişe kadar kanban pano",
            "Günlük has altın & işçilik fiyat motoru",
            "5 ustaya kadar personel yetki yönetimi",
            "WhatsApp / SMS durum bildirimleri",
        ),
        is_paid=True,
        is_popular=True,
    ),
    "usta_pro": Plan(
        code="usta_pro",
        name="Usta Pro",
        tagline="Yüksek hacimli imalathaneler ve çok ustalıklı atölyeler",
        monthly_price_tl=1950,
        monthly_order_limit=None,
        max_staff=None,
        features=(
            "Sınırsız aylık sipariş ve sınırsız usta hesabı",
            "Maliyet + kâr (GOLD_COST_PLUS) ve toplu fiyat güncelleme",
            "Öncelikli kurulum ve birebir veri aktarımı desteği",
        ),
        is_paid=True,
    ),
}

DEFAULT_PLAN_CODE = "baslangic"


def get_plan(plan_code: str | None) -> Plan:
    if not plan_code:
        return PLANS[DEFAULT_PLAN_CODE]
    key = plan_code.strip().lower()
    # Eski kodlarla geriye dönük uyumluluk
    aliases = {"free": "baslangic", "pro": "atolye", "studio": "usta_pro"}
    key = aliases.get(key, key)
    return PLANS.get(key, PLANS[DEFAULT_PLAN_CODE])


def list_plans() -> list[Plan]:
    return list(PLANS.values())


def list_paid_plans() -> list[Plan]:
    return [p for p in PLANS.values() if p.is_paid]


def effective_monthly_price(plan_code: str | None, is_pilot: bool = False) -> int:
    plan = get_plan(plan_code)
    return plan.pilot_price_tl() if is_pilot else plan.monthly_price_tl


def remaining_orders(plan_code: str | None, monthly_order_count: int) -> int | None:
    if monthly_order_count < 0:
        raise ValueError("Aylık sipariş sayısı negatif olamaz")
    plan = get_plan(plan_code)
    if plan.monthly_order_limit is None:
        return None
    return max(0, plan.monthly_order_limit - monthly_order_count)


def can_create_order(plan_code: str | None, monthly_order_count: int) -> bool:
    if monthly_order_count < 0:
        raise ValueError("Aylık sipariş sayısı negatif olamaz")
    plan = get_plan(plan_code)
    if plan.monthly_order_limit is None:
        return True
    return monthly_order_count < plan.monthly_order_limit
