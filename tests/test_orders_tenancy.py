import io
import re

from tests.conftest import csrf, make_client, make_image, register, seed_order

PNG = make_image((800, 600), "PNG")


def test_order_flow_and_notification(app, notifier):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    page = c.get(f"/siparisler/{oid}").text
    assert "2.400,00 ₺" in page  # 2 × 1000 + %20 KDV

    t = csrf(c)
    c.post(f"/siparisler/{oid}/durum", data={"csrf_token": t, "to_status": "IN_PRODUCTION"})
    assert "Üretimde" in c.get(f"/siparisler/{oid}").text
    assert len(notifier.sent) == 1
    assert "Mehmet" in notifier.sent[0][1] and "/t/" in notifier.sent[0][1]

    # Geçersiz geçiş: Üretimde → Teslim edildi olmaz, durum değişmez
    c.post(f"/siparisler/{oid}/durum", data={"csrf_token": t, "to_status": "DELIVERED"})
    assert len(notifier.sent) == 1


def test_no_notification_without_consent(app, notifier):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c, consent=False)
    c.post(f"/siparisler/{oid}/durum", data={"csrf_token": csrf(c), "to_status": "IN_PRODUCTION"})
    assert notifier.sent == []


def test_tenant_isolation_idor(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@ornek.com")
    register(b, "atolye-b", "b@ornek.com")
    oid = seed_order(a)
    tb = csrf(b)
    assert b.get(f"/siparisler/{oid}").status_code == 404
    assert b.post(f"/siparisler/{oid}/durum", data={"csrf_token": tb, "to_status": "CANCELLED"}).status_code == 404
    assert b.get("/urunler/1/fiyat").status_code == 404
    assert "Mehmet" not in b.get("/musteriler").text
    # B, A'nın müşterisiyle sipariş açamaz
    r = b.post("/siparisler", data={"csrf_token": tb, "customer_id": "1", "product_id": "1", "quantity": "1"})
    assert r.status_code == 404


def test_tracking_page_hides_pii(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    code = re.search(r"/t/([\w-]+)</code>", c.get(f"/siparisler/{oid}").text).group(1)
    public = make_client(app).get(f"/t/{code}")
    assert public.status_code == 200
    assert "Mehmet" in public.text
    assert "Yılmaz" not in public.text and "0532" not in public.text
    assert make_client(app).get("/t/tahminedilemez123").status_code == 404


def test_upload_validation_and_public_media(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    t = csrf(c)
    # Uzantısı .jpg ama içeriği metin → red
    r = c.post(f"/siparisler/{oid}/medya", data={"csrf_token": t},
               files={"file": ("x.jpg", io.BytesIO(b"<?php echo 1; ?>"), "image/jpeg")})
    assert r.status_code == 400
    # 1 MB sınırı
    r = c.post(f"/siparisler/{oid}/medya", data={"csrf_token": t},
               files={"file": ("big.png", io.BytesIO(PNG + b"\x00" * 1_100_000), "image/png")})
    assert r.status_code == 400
    # Geçerli PNG
    r = c.post(f"/siparisler/{oid}/medya", data={"csrf_token": t, "is_public": "true", "caption": "Kalıp"},
               files={"file": ("../../etc/passwd.png", io.BytesIO(PNG), "image/png")})
    assert r.status_code == 303
    detail = c.get(f"/siparisler/{oid}").text
    mid = re.search(r'href="/medya/(\d+)"', detail).group(1)
    assert c.get(f"/medya/{mid}").headers["content-type"] == "image/png"
    code = re.search(r"/t/([\w-]+)</code>", detail).group(1)
    assert make_client(app).get(f"/t/{code}/medya/{mid}").status_code == 200
    # Başka atölye medyaya erişemez
    b = make_client(app)
    register(b, "atolye-b", "b@ornek.com")
    assert b.get(f"/medya/{mid}").status_code == 404


def test_gold_product_pricing_preview(app):
    c = make_client(app)
    register(c, "kuyumcu", "k@ornek.com")
    t = csrf(c)
    c.post("/urunler", data={"csrf_token": t, "name": "22 Ayar Bilezik", "pricing_type": "GOLD",
                             "weight_g": "5", "purity_milyem": "916", "labor_milyem": "30", "extra_cost": "0",
                             "show_in_showcase": "true"})
    assert "altın fiyatı girilmemiş" in c.get("/urunler/1/fiyat").text
    c.post("/atolye/altin-fiyati", data={"csrf_token": t, "price": "3000"})
    frag = c.get("/urunler/1/fiyat?adet=1").text
    assert "17.028,00 ₺" in frag
    assert "17.028,00 ₺" in make_client(app).get("/v/kuyumcu").text
