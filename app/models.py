"""Tüm modelleri tek yerden yükler (Alembic autogenerate ve create_all için)."""
from app.core.db import Base
from app.modules.auth.models import PasswordResetToken, Role, User, UserSession
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.media.models import Media
from app.modules.notifications.models import Notification, NotificationStatus
from app.modules.orders.models import Order, OrderEvent, OrderItem
from app.modules.payments.models import ProcessedWebhook
from app.modules.workshop.models import Workshop

__all__ = [
    "Base", "Customer", "Media", "Notification", "NotificationStatus", "Order", "OrderEvent",
    "OrderItem", "ProcessedWebhook", "Product", "PasswordResetToken", "Role", "User", "UserSession", "Workshop",
]
