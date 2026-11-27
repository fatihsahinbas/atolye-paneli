"""H2 PROJE (Çınar) · Çok kalemli sipariş."""
import re
from decimal import Decimal

from app.modules.orders.models import Order
from tests.conftest import csrf, make_client, register


def _setup(c):
    t = csrf(c)
    c.post("/musteriler", data={"csrf_token": t, "full_name": "Ali Veli", "phone": "0532 111 22 33"})
    c.post("/urunler", data={"csrf_token": t, "name": "Tablo", "pricing_type": "FIXED", "base_price": "1000"})
    c.post("/urunler", data={"csrf_token": t, "name": "Çerçeve", "pricing_type": "FIXED", "base_price": "250"})
    page = c.get("/siparisler/yeni").text
    cid = re.search(r'name="customer_id"[^>]*>\s*<option value="(\d+)"', page).group(1)
    return t, cid


def test_two_items_total_is_sum(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    t, cid = _setup(c)
    r = c.post("/siparisler", data={
        "csrf_token": t, "customer_id": cid,
        "product_id": ["1", "2"], "quantity": ["2", "3"], "description": ["İsimli", ""],
    })
    assert r.status_code == 303, r.text
    oid = int(r.headers["location"].rsplit("/", 1)[1])
    with app.state.SessionLocal() as db:
        o = db.get(Order, oid)
        assert len(o.items) == 2
        assert o.total_net == Decimal("2750.00")  # 2×1000 + 3×250
        assert o.items[0].description == "İsimli"
        assert o.items[1].description == "Çerçeve"


def test_preview_matches_order_total(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    t, _ = _setup(c)
    r = c.post("/siparisler/fiyat-onizleme", data={"product_id": ["1", "2"], "quantity": ["2", "3"]},
               headers={"X-CSRF-Token": t})
    assert r.status_code == 200
    assert "2.750,00 ₺" in r.text


def test_new_item_row_and_remove(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    t, _ = _setup(c)
    r = c.get("/siparisler/kalem/yeni")
    assert r.status_code == 200 and 'name="product_id"' in r.text
    assert c.post("/siparisler/kalem/sil", headers={"X-CSRF-Token": t}).status_code == 200


def test_empty_or_mismatched_items_rejected(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    t, cid = _setup(c)
    r = c.post("/siparisler", data={"csrf_token": t, "customer_id": cid})
    assert r.status_code == 200 and "En az bir ürün" in r.text
    r = c.post("/siparisler", data={"csrf_token": t, "customer_id": cid, "product_id": ["1", "2"], "quantity": ["1"]})
    assert "eşleşmiyor" in r.text
    r = c.post("/siparisler", data={"csrf_token": t, "customer_id": cid, "product_id": ["1"], "quantity": ["0"]})
    assert "1 ile 1000" in r.text


def test_other_workshop_product_is_404(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@ornek.com")
    _setup(a)
    register(b, "atolye-b", "b@ornek.com")
    tb = csrf(b)
    b.post("/musteriler", data={"csrf_token": tb, "full_name": "B Müşteri", "phone": "0532 222 33 44"})
    page = b.get("/siparisler/yeni").text
    assert "Tablo" not in page
    r = b.post("/siparisler/fiyat-onizleme", data={"product_id": ["1"], "quantity": ["1"]},
               headers={"X-CSRF-Token": tb})
    assert r.status_code == 404


def test_inactive_product_cannot_be_ordered(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    t, cid = _setup(c)
    c.post("/urunler/2/duzenle", data={"csrf_token": csrf(c, "/urunler/2/duzenle"), "name": "Çerçeve",
                                       "pricing_type": "FIXED", "base_price": "250"})  # is_active işaretsiz
    r = c.post("/siparisler", data={"csrf_token": t, "customer_id": cid, "product_id": ["2"], "quantity": ["1"]})
    assert r.status_code == 200 and "Pasif ürün" in r.text
