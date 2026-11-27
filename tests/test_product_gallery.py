"""H3 PROJE 7 · Ürün görseli yükleme + galeri + vitrin kapağı."""
from pathlib import Path

from app.modules.media.models import Media
from app.modules.media.service import thumb_name
from tests.conftest import csrf, make_client, make_image, register


def _product(c, name="Gül Tablo"):
    c.post("/urunler", data={"csrf_token": csrf(c), "name": name, "pricing_type": "FIXED", "base_price": "500",
                             "show_in_showcase": "true"})


def _upload(c, pid, n=1):
    files = [("files", (f"g{i}.jpg", make_image((60, 60), "JPEG"), "image/jpeg")) for i in range(n)]
    return c.post(f"/urunler/{pid}/gorsel", data={"csrf_token": csrf(c, f"/urunler/{pid}/duzenle")}, files=files)


def _images(app, pid=1):
    with app.state.SessionLocal() as db:
        return db.query(Media).filter_by(product_id=pid).order_by(Media.id).all()


def test_upload_three_first_is_cover_then_change(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    _product(c)
    assert _upload(c, 1, 3).status_code == 303
    imgs = _images(app)
    assert len(imgs) == 3 and [m.is_cover for m in imgs] == [True, False, False]
    c.post(f"/gorsel/{imgs[1].id}/kapak", data={"csrf_token": csrf(c)})
    assert [m.is_cover for m in _images(app)] == [False, True, False]


def test_delete_removes_db_row_and_files(app, settings):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    _product(c)
    _upload(c, 1, 2)
    first = _images(app)[0]
    root = Path(settings.media_root)
    assert (root / first.stored_name).exists() and (root / thumb_name(first.stored_name)).exists()
    c.post(f"/gorsel/{first.id}/sil", data={"csrf_token": csrf(c)})
    rest = _images(app)
    assert [m.id for m in rest] != [first.id] and len(rest) == 1
    assert rest[0].is_cover  # kapak silinince sıradaki kapak olur
    assert not (root / first.stored_name).exists()
    assert not (root / thumb_name(first.stored_name)).exists()


def test_other_workshop_cannot_cover_or_delete(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@ornek.com")
    register(b, "atolye-b", "b@ornek.com")
    _product(a)
    _upload(a, 1)
    mid = _images(app)[0].id
    assert b.post(f"/gorsel/{mid}/kapak", data={"csrf_token": csrf(b)}).status_code == 404
    assert b.post(f"/gorsel/{mid}/sil", data={"csrf_token": csrf(b)}).status_code == 404
    assert _upload(b, 1).status_code == 404


def test_showcase_shows_cover_and_hides_inactive(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    _product(c)
    _upload(c, 1)
    mid = _images(app)[0].id
    pub = make_client(app)
    html = pub.get("/v/atolye-a").text
    assert f"/v/atolye-a/gorsel/{mid}?boyut=kucuk" in html
    r = pub.get(f"/v/atolye-a/gorsel/{mid}?boyut=kucuk")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    # Başka atölyenin slug'ıyla → 404
    register(make_client(app), "atolye-b", "b@ornek.com")
    assert pub.get(f"/v/atolye-b/gorsel/{mid}").status_code == 404
    # Ürün pasif → 404
    c.post("/urunler/1/duzenle", data={"csrf_token": csrf(c, "/urunler/1/duzenle"), "name": "Gül Tablo",
                                       "pricing_type": "FIXED", "base_price": "500", "show_in_showcase": "true"})
    assert pub.get(f"/v/atolye-a/gorsel/{mid}").status_code == 404


def test_order_media_not_public_via_showcase(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    from tests.conftest import seed_order
    oid = seed_order(c)
    c.post(f"/siparisler/{oid}/medya", data={"csrf_token": csrf(c)},
           files={"file": ("x.jpg", make_image((40, 40), "JPEG"), "image/jpeg")})
    with app.state.SessionLocal() as db:
        mid = db.query(Media).filter_by(order_id=oid).one().id
    assert make_client(app).get(f"/v/atolye-a/gorsel/{mid}").status_code == 404
