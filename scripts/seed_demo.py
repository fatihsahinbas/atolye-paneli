"""Demo verisi: ders ve sunum için örnek atölye, ürün, müşteri ve siparişler.

Kullanım:  python -m scripts.seed_demo
Giriş:     demo@atolye.local / demo-sifre-123
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app import models  # noqa: F401
from app.core.config import get_settings
from app.core.db import Base, build_engine, build_sessionmaker, utcnow
from app.core.security import hash_password
from app.domain.order_status import OrderStatus
from app.domain.pricing import PricingType
from app.modules.auth.models import Role, User
from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.orders.service import NewItem, change_status, create_order
from app.modules.workshop.models import Workshop


def main() -> None:
    engine = build_engine(get_settings().database_url)
    Base.metadata.create_all(engine)
    db = build_sessionmaker(engine)()
    if db.scalar(select(Workshop).where(Workshop.slug == "demo-atolye")):
        print("Demo zaten var.")
        return
    ws = Workshop(name="Işık Kuyumculuk & Filografi", slug="demo-atolye",
                  gold_price_per_gram=Decimal("3000"), gold_price_updated_at=utcnow())
    db.add(ws)
    db.flush()
    user = User(workshop_id=ws.id, email="demo@atolye.local", full_name="Demo Usta",
                password_hash=hash_password("demo-sifre-123"), role=Role.OWNER)
    db.add(user)
    db.add_all([
        Product(workshop_id=ws.id, name="22 Ayar Burgu Bilezik", pricing_type=PricingType.GOLD,
                weight_g=Decimal("12"), purity_milyem=916, labor_milyem=25,
                description="El işçiliği, kişiye özel ölçü"),
        Product(workshop_id=ws.id, name="14 Ayar İsimli Kolye", pricing_type=PricingType.GOLD,
                weight_g=Decimal("3.2"), purity_milyem=585, labor_milyem=120, extra_cost=Decimal("250"),
                description="İstediğiniz isim, el yazısı font"),
        Product(workshop_id=ws.id, name="Filografi Portre 50×70", pricing_type=PricingType.FIXED,
                base_price=Decimal("2500"), description="Fotoğraftan çivi-ip portre"),
        Product(workshop_id=ws.id, name="Filografi Harf Pano", pricing_type=PricingType.FIXED,
                base_price=Decimal("900"), description="Baş harf, renk seçimli"),
    ])
    names = [("Elif Kaya", "05321112233"), ("Murat Demir", "05337778899"), ("Zeynep Arslan", "05445556677"),
             ("Burak Çelik", "05059998877"), ("Selin Aydın", "05301234567"), ("Emre Şahin", "05427654321")]
    customers = [Customer(workshop_id=ws.id, full_name=n, phone=p, contact_consent_at=utcnow()) for n, p in names]
    db.add_all(customers)
    db.commit()

    products = db.scalars(select(Product).where(Product.workshop_id == ws.id)).all()
    plan = [
        (0, 2, 1, [], 6), (1, 0, 1, [OrderStatus.DESIGN_APPROVAL], 9),
        (2, 3, 2, [OrderStatus.IN_PRODUCTION], 3), (3, 1, 1, [OrderStatus.IN_PRODUCTION], -1),
        (4, 0, 1, [OrderStatus.IN_PRODUCTION, OrderStatus.QUALITY_CHECK], 2),
        (5, 2, 1, [OrderStatus.IN_PRODUCTION, OrderStatus.QUALITY_CHECK, OrderStatus.SHIPPED], 1),
        (0, 3, 1, [OrderStatus.IN_PRODUCTION, OrderStatus.QUALITY_CHECK, OrderStatus.DELIVERED], -3),
    ]
    for ci, pi, qty, steps, due in plan:
        o = create_order(db, user, customers[ci].id, [NewItem(products[pi].id, qty)],
                         date.today() + timedelta(days=due))
        for s in steps:
            change_status(db, user, o, s)
    print("Demo hazır → demo@atolye.local / demo-sifre-123")


if __name__ == "__main__":
    main()
