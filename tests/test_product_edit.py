from sqlalchemy import select

from app.modules.catalog.models import Product
from app.modules.orders.models import OrderItem
from tests.conftest import csrf, make_client, register, seed_order


def test_owner_updates_product_and_flags(app):
    c = make_client(app)
    register(c, "atolye-a", "owner-a@ornek.com")
    t = csrf(c)
    c.post(
        "/urunler",
        data={
            "csrf_token": t,
            "name": "Klasik Yüzük",
            "pricing_type": "FIXED",
            "base_price": "1200",
            "show_in_showcase": "true",
        },
    )
    list_html = c.get("/urunler").text
    assert 'href="/urunler/1/duzenle"' in list_html

    r = c.post(
        "/urunler/1/duzenle",
        data={
            "csrf_token": csrf(c, "/urunler/1/duzenle"),
            "name": "Klasik Yüzük Güncel",
            "pricing_type": "FIXED",
            "base_price": "1850",
            "extra_cost": "100",
            "show_in_showcase": "",
        },
    )
    assert r.status_code == 303

    with app.state.SessionLocal() as db:
        p = db.get(Product, 1)
        assert p is not None
        assert p.name == "Klasik Yüzük Güncel"
        assert str(p.base_price) == "1850.00"
        assert p.is_active is False
        assert p.show_in_showcase is False


def test_other_owner_cannot_edit_product_returns_404(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@ornek.com")
    register(b, "atolye-b", "b@ornek.com")

    ta = csrf(a)
    a.post(
        "/urunler",
        data={
            "csrf_token": ta,
            "name": "A Ürünü",
            "pricing_type": "FIXED",
            "base_price": "2000",
            "show_in_showcase": "true",
        },
    )

    tb = csrf(b)
    assert b.get("/urunler/1/duzenle").status_code == 404
    res = b.post(
        "/urunler/1/duzenle",
        data={
            "csrf_token": tb,
            "name": "Çalınmış Ad",
            "pricing_type": "FIXED",
            "base_price": "1",
            "is_active": "true",
        },
    )
    assert res.status_code == 404

    with app.state.SessionLocal() as db:
        p = db.get(Product, 1)
        assert p is not None
        assert p.name == "A Ürünü"
        assert str(p.base_price) == "2000.00"


def test_staff_gets_403_on_product_edit(app):
    owner = make_client(app)
    register(owner, "atolye-s", "owner@ornek.com")
    t = csrf(owner)
    owner.post(
        "/urunler",
        data={
            "csrf_token": t,
            "name": "Kolye",
            "pricing_type": "FIXED",
            "base_price": "1500",
            "show_in_showcase": "true",
        },
    )
    owner.post(
        "/personel",
        data={
            "csrf_token": csrf(owner, "/personel"),
            "full_name": "Usta Personel",
            "email": "staff@ornek.com",
            "password": "guclu-sifre-123",
        },
    )

    staff = make_client(app)
    login_res = staff.post("/giris", data={"email": "staff@ornek.com", "password": "guclu-sifre-123"})
    assert login_res.status_code == 303
    assert staff.get("/urunler/1/duzenle").status_code == 403
    assert staff.post(
        "/urunler/1/duzenle",
        data={"csrf_token": csrf(staff), "name": "Yetkisiz", "pricing_type": "FIXED", "base_price": "100"},
    ).status_code == 403


def test_invalid_price_keeps_db_unchanged(app):
    c = make_client(app)
    register(c, "atolye-inv", "inv@ornek.com")
    t = csrf(c)
    c.post(
        "/urunler",
        data={
            "csrf_token": t,
            "name": "Bileklik",
            "pricing_type": "FIXED",
            "base_price": "2500",
            "is_active": "true",
            "show_in_showcase": "true",
        },
    )

    r = c.post(
        "/urunler/1/duzenle",
        data={
            "csrf_token": csrf(c, "/urunler/1/duzenle"),
            "name": "Bileklik Hatalı",
            "pricing_type": "FIXED",
            "base_price": "-50",
            "is_active": "true",
        },
    )
    assert r.status_code == 200

    with app.state.SessionLocal() as db:
        p = db.get(Product, 1)
        assert p is not None
        assert p.name == "Bileklik"
        assert str(p.base_price) == "2500.00"


def test_editing_product_does_not_change_existing_order_item_prices(app):
    c = make_client(app)
    register(c, "atolye-freeze", "freeze@ornek.com")
    oid = seed_order(c)

    r = c.post(
        "/urunler/1/duzenle",
        data={
            "csrf_token": csrf(c, "/urunler/1/duzenle"),
            "name": "Filografi Tablo",
            "pricing_type": "FIXED",
            "base_price": "9999",
            "is_active": "true",
            "show_in_showcase": "true",
        },
    )
    assert r.status_code == 303

    with app.state.SessionLocal() as db:
        item = db.scalar(select(OrderItem).where(OrderItem.order_id == oid))
        assert item is not None
        assert str(item.unit_net) == "1000.00"
        assert str(item.line_net) == "2000.00"


def test_invalid_edit_keeps_submitted_values(app):
    c = make_client(app)
    register(c, "atolye-v", "owner-v@ornek.com")
    c.post(
        "/urunler",
        data={"csrf_token": csrf(c), "name": "Yüzük", "pricing_type": "FIXED", "base_price": "100"},
    )
    r = c.post(
        "/urunler/1/duzenle",
        data={
            "csrf_token": csrf(c, "/urunler/1/duzenle"),
            "name": "Yeni Ad",
            "pricing_type": "FIXED",
            "base_price": "abc",
        },
    )
    assert r.status_code == 200
    assert 'value="Yeni Ad"' in r.text
    assert 'class="alert"' in r.text
