"""H3 PROJE 4 · KVKK sayfası + iki ayrı izin."""
from app.modules.customers.models import Customer
from tests.conftest import csrf, make_client, register, seed_order


def test_kvkk_public_and_placeholder(app):
    c = make_client(app)
    r = c.get("/kvkk")
    assert r.status_code == 200
    assert "[ATÖLYE ADI]" in r.text
    assert "Son güncelleme" in r.text
    register(c, "atolye-a", "a@ornek.com")
    r = make_client(app).get("/kvkk?atolye=atolye-a")
    assert "atolye-a atölye" in r.text and "[ATÖLYE ADI]" not in r.text


def test_kvkk_links_on_register_showcase_tracking(app):
    c = make_client(app)
    assert 'href="/kvkk"' in c.get("/kayit").text
    register(c, "atolye-a", "a@ornek.com")
    assert "/kvkk?atolye=atolye-a" in make_client(app).get("/v/atolye-a").text


def test_marketing_consent_default_off(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    c.post("/musteriler", data={"csrf_token": csrf(c), "full_name": "Ali Veli", "consent": "true"})
    with app.state.SessionLocal() as db:
        cu = db.query(Customer).one()
        assert cu.contact_consent_at is not None
        assert cu.marketing_consent_at is None


def test_revoking_consent_clears_timestamp_and_skips_notification(app, notifier):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c, consent=True)
    with app.state.SessionLocal() as db:
        cid = db.query(Customer).one().id
    r = c.post(f"/musteriler/{cid}/duzenle", data={
        "csrf_token": csrf(c, f"/musteriler/{cid}/duzenle"),
        "full_name": "Mehmet Yılmaz", "phone": "0532 111 22 33", "marketing": "true",
    })
    assert r.status_code == 303
    with app.state.SessionLocal() as db:
        cu = db.get(Customer, cid)
        assert cu.contact_consent_at is None
        assert cu.marketing_consent_at is not None
    c.post(f"/siparisler/{oid}/durum", data={"csrf_token": csrf(c), "to_status": "IN_PRODUCTION"})
    assert notifier.sent == []


def test_other_workshop_cannot_edit_customer(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@ornek.com")
    register(b, "atolye-b", "b@ornek.com")
    a.post("/musteriler", data={"csrf_token": csrf(a), "full_name": "Ali Veli"})
    assert b.get("/musteriler/1/duzenle").status_code == 404
    r = b.post("/musteriler/1/duzenle", data={"csrf_token": csrf(b), "full_name": "Hack"})
    assert r.status_code == 404
