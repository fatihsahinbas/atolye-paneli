"""Sipariş yaşam döngüsü — state machine.  Sahip: Çınar

Kural: durum değişikliği YALNIZCA ensure_transition() üzerinden yapılır.
"""
from enum import StrEnum


class OrderStatus(StrEnum):
    RECEIVED = "RECEIVED"
    DESIGN_APPROVAL = "DESIGN_APPROVAL"
    IN_PRODUCTION = "IN_PRODUCTION"
    QUALITY_CHECK = "QUALITY_CHECK"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


LABELS: dict[OrderStatus, str] = {
    OrderStatus.RECEIVED: "Sipariş alındı",
    OrderStatus.DESIGN_APPROVAL: "Tasarım onayı",
    OrderStatus.IN_PRODUCTION: "Üretimde",
    OrderStatus.QUALITY_CHECK: "Kalite kontrol",
    OrderStatus.SHIPPED: "Kargoda",
    OrderStatus.DELIVERED: "Teslim edildi",
    OrderStatus.CANCELLED: "İptal",
}

# Kanban sütun sırası (iptal hariç)
BOARD_ORDER: list[OrderStatus] = [
    OrderStatus.RECEIVED,
    OrderStatus.DESIGN_APPROVAL,
    OrderStatus.IN_PRODUCTION,
    OrderStatus.QUALITY_CHECK,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
]

TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.RECEIVED: frozenset({OrderStatus.DESIGN_APPROVAL, OrderStatus.IN_PRODUCTION, OrderStatus.CANCELLED}),
    OrderStatus.DESIGN_APPROVAL: frozenset({OrderStatus.IN_PRODUCTION, OrderStatus.RECEIVED, OrderStatus.CANCELLED}),
    OrderStatus.IN_PRODUCTION: frozenset({OrderStatus.QUALITY_CHECK, OrderStatus.CANCELLED}),
    OrderStatus.QUALITY_CHECK: frozenset({OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.IN_PRODUCTION}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


class InvalidTransition(ValueError):
    def __init__(self, current: OrderStatus, target: OrderStatus) -> None:
        super().__init__(f"{LABELS[current]} → {LABELS[target]} geçişi yapılamaz")
        self.current = current
        self.target = target


def allowed_next(current: OrderStatus) -> list[OrderStatus]:
    return sorted(TRANSITIONS[current], key=lambda s: list(OrderStatus).index(s))


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in TRANSITIONS[current]


def ensure_transition(current: OrderStatus, target: OrderStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransition(current, target)


def is_terminal(status: OrderStatus) -> bool:
    return not TRANSITIONS[status]
