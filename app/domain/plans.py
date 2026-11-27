"""Abonelik paketleri ve aylık sipariş sınırı. Sahip: Hayrettin · ortak arayüz: Hasan (ödeme)

Saf Python: DB, FastAPI, ayar yok. Ödeme modülü tutarı `get_plan(code).monthly_price`'tan okur.
Paket fiyatları H1 görüşmelerinden (docs/H4_PAKET_TABLOSU.md). Pilot atölyeler ücretsizdir
(docs/KARARLAR.md, 13 Kasım); pilotluk `Workshop.is_pilot` ile anlaşılır, `PILOT` paketi onların kaydıdır.
"""
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Plan:
    code: str                         # "BASLANGIC", "ATOLYE", "USTA_PRO", "PILOT"
    name: str                         # ekranda görünen ad
    monthly_price: Decimal            # KDV dahil, TL
    max_orders_per_month: int | None  # None = sınırsız
    tagline: str = ""
    features: tuple[str, ...] = field(default_factory=tuple)
    is_popular: bool = False
    is_public: bool = True            # /fiyatlar sayfasında görünsün mü

    @property
    def is_paid(self) -> bool:
        return self.monthly_price > 0


PILOT = Plan(
    "PILOT", "Pilot (ücretsiz)", Decimal("0"), None,
    tagline="Demo gününe kadar pilot programındaki atölyeler",
    is_public=False,
)
BASLANGIC = Plan(
    "BASLANGIC", "Başlangıç", Decimal("0"), 20,
    tagline="Yeni kurulan, ayda 10–20 özel sipariş alan atölyeler",
    features=(
        "Aylık 20 siparişe kadar takip",
        "Ürün kataloğu ve atölye vitrini",
        "Müşteri takip linki",
    ),
)
ATOLYE = Plan(
    "ATOLYE", "Atölye", Decimal("950.00"), 150,
    tagline="Kuyumcu ve düzenli sipariş alan büyüyen atölyeler",
    features=(
        "Aylık 150 siparişe kadar üretim panosu",
        "Altın fiyatına bağlı fiyat motoru",
        "Usta (personel) hesapları",
        "SMS / WhatsApp / e-posta durum bildirimleri",
    ),
    is_popular=True,
)
USTA_PRO = Plan(
    "USTA_PRO", "Usta Pro", Decimal("1950.00"), None,
    tagline="Yüksek hacimli, çok ustalı imalathaneler",
    features=(
        "Sınırsız sipariş",
        "Atölye paketindeki her şey",
        "Kurulum ve veri aktarımında birebir destek",
    ),
)

PLANS: dict[str, Plan] = {p.code: p for p in [BASLANGIC, ATOLYE, USTA_PRO, PILOT]}


def get_plan(code: str) -> Plan:
    try:
        return PLANS[code]
    except KeyError:
        raise ValueError(f"Bilinmeyen paket: {code}") from None


def public_plans() -> list[Plan]:
    """/fiyatlar sayfasında gösterilecek paketler (PILOT hariç)."""
    return [p for p in PLANS.values() if p.is_public]


def paid_plans() -> list[Plan]:
    """Abonelik ekranında satın alınabilen paketler."""
    return [p for p in PLANS.values() if p.is_paid]


def can_create_order(plan: Plan, orders_this_month: int) -> bool:
    if orders_this_month < 0:
        raise ValueError("Aylık sipariş sayısı negatif olamaz")
    if plan.max_orders_per_month is None:
        return True
    return orders_this_month < plan.max_orders_per_month


def remaining_orders(plan: Plan, orders_this_month: int) -> int | None:
    if orders_this_month < 0:
        raise ValueError("Aylık sipariş sayısı negatif olamaz")
    if plan.max_orders_per_month is None:
        return None
    return max(0, plan.max_orders_per_month - orders_this_month)
