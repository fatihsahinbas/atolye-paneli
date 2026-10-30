"""Sipariş iş kuralları.  Sahip: Çınar"""
import secrets
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.tenancy import get_owned
from app.domain.order_status import OrderStatus, ensure_transition
from app.modules.auth.models import User
from app.modules.catalog.models import Product
from app.modules.catalog.service import quote
from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderEvent, OrderItem
from app.modules.workshop.models import Workshop


@dataclass(frozen=True)
class NewItem:
    product_id: int
    quantity: int
    description: str | None = None


def new_tracking_code() -> str:
    return secrets.token_urlsafe(9)  # 12 karakter, tahmin edilemez


def create_order(
    db: Session,
    user: User,
    customer_id: int,
    items: list[NewItem],
    due_date: date | None = None,
    note: str | None = None,
) -> Order:
    """Fiyatlar sipariş anında hesaplanıp dondurulur. PricingError fırlatabilir."""
    if not items:
        raise ValueError("En az bir kalem gerekli")
    customer = get_owned(db, Customer, customer_id, user)  # başka atölyenin müşterisi → 404
    workshop = db.get(Workshop, user.workshop_id)
    order = Order(
        workshop_id=user.workshop_id,
        customer_id=customer.id,
        tracking_code=new_tracking_code(),
        due_date=due_date,
        note=note,
    )
    total_net = total_gross = Decimal(0)
    for it in items:
        product = get_owned(db, Product, it.product_id, user)
        unit = quote(product, workshop, 1)
        line = unit.times(it.quantity)
        order.items.append(
            OrderItem(
                product_id=product.id,
                description=(it.description or product.name)[:200],
                quantity=it.quantity,
                unit_net=unit.net,
                line_net=line.net,
                line_gross=line.gross,
            )
        )
        total_net += line.net
        total_gross += line.gross
    order.total_net, order.total_gross = total_net, total_gross
    order.events.append(OrderEvent(from_status=None, to_status=OrderStatus.RECEIVED, actor_user_id=user.id))
    db.add(order)
    db.commit()
    return order


def change_status(db: Session, user: User, order: Order, target: OrderStatus, note: str | None = None) -> Order:
    """InvalidTransition fırlatabilir. Bildirimi çağıran taraf (router) tetikler."""
    if order.workshop_id != user.workshop_id:  # savunma derinliği
        raise PermissionError
    ensure_transition(order.status, target)
    order.events.append(
        OrderEvent(from_status=order.status, to_status=target, note=(note or None), actor_user_id=user.id)
    )
    order.status = target
    db.commit()
    return order
