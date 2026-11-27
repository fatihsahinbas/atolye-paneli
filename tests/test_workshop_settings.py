"""H4 · Atölye ayarları (/atolye/ayarlar): ad + telefon."""
from sqlalchemy import select

from app.modules.workshop.models import Workshop
from tests.conftest import csrf, make_client, register

PAGE = "/atolye/ayarlar"


def _ws(app, slug: str) -> Workshop:
    with app.state.SessionLocal() as db:
        return db.scalar(select(Workshop).where(Workshop.slug == slug))


def _save(client, name: str, phone: str, token: str | None = None):
    return client.post(PAGE, data={"csrf_token": token or csrf(client, PAGE), "name": name, "phone": phone})


def _add_showcase_product(client) -> None:
    client.post("/urunler", data={"csrf_token": csrf(client), "name": "Filografi Tablo", "pricing_type": "FIXED",
                                  "base_price": "1000", "show_in_showcase": "true"})


def test_owner_saves_phone_in_e164(app):
    c = make_client(app)
    register(c, "filo", "a@example.com")
    r = _save(c, "Filo Atölye", "0532 111 22 33")
    assert r.status_code == 303
    assert r.headers["location"] == f"{PAGE}?kaydedildi=1"
    ws = _ws(app, "filo")
    assert ws.phone == "+905321112233"
    assert ws.name == "Filo Atölye"
    assert "Kaydedildi" in c.get(r.headers["location"]).text


def test_invalid_input_shows_error_and_db_unchanged(app):
    c = make_client(app)
    register(c, "filo", "a@example.com")
    before = _ws(app, "filo")
    r = _save(c, "Yeni Ad", "123")
    assert r.status_code == 422
    assert "Geçersiz telefon" in r.text
    assert 'value="123"' in r.text  # kullanıcının yazdığı kaybolmaz
    r = _save(c, "A", "")
    assert r.status_code == 422
    after = _ws(app, "filo")
    assert (after.name, after.phone) == (before.name, before.phone)


def test_whatsapp_button_follows_saved_phone(app):
    c = make_client(app)
    register(c, "filo", "a@example.com")
    _add_showcase_product(c)
    public = make_client(app)
    assert "wa.me" not in public.get("/v/filo").text
    _save(c, "Filo Atölye", "+90 532 111 22 33")
    assert "wa.me/905321112233" in public.get("/v/filo").text
    _save(c, "Filo Atölye", "")
    assert _ws(app, "filo").phone is None
    assert "wa.me" not in public.get("/v/filo").text


def test_slug_cannot_be_changed(app):
    c = make_client(app)
    register(c, "filo", "a@example.com")
    c.post(PAGE, data={"csrf_token": csrf(c, PAGE), "name": "Filo Atölye", "phone": "", "slug": "baska"})
    assert _ws(app, "filo") is not None
    assert _ws(app, "baska") is None


def test_csrf_required(app):
    c = make_client(app)
    register(c, "filo", "a@example.com")
    assert _save(c, "Ele Geçirildi", "", token="yanlis").status_code == 403
    assert c.post(PAGE, data={"name": "Ele Geçirildi", "phone": ""}).status_code == 403
    assert _ws(app, "filo").name != "Ele Geçirildi"


def test_staff_forbidden_and_link_owner_only(app):
    owner = make_client(app)
    register(owner, "filo", "a@example.com")
    assert f'href="{PAGE}"' in owner.get("/musteriler").text
    owner.post("/personel", data={"csrf_token": csrf(owner, "/personel"), "full_name": "Usta Bir",
                                  "email": "usta@example.com", "password": "guclu-sifre-123"})
    staff = make_client(app)
    assert staff.post("/giris", data={"email": "usta@example.com", "password": "guclu-sifre-123"}).status_code == 303
    assert staff.get(PAGE).status_code == 403
    assert _save(staff, "Personel Değiştirdi", "", token=csrf(staff)).status_code == 403
    assert f'href="{PAGE}"' not in staff.get("/musteriler").text
    assert _ws(app, "filo").name != "Personel Değiştirdi"


def test_each_owner_edits_only_own_workshop(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@example.com")
    register(b, "atolye-b", "b@example.com")
    _save(b, "B Yeni Ad", "0532 999 88 77")
    assert _ws(app, "atolye-a").name == "atolye-a atölye"
    assert _ws(app, "atolye-a").phone is None
    assert "atolye-a atölye" in a.get(PAGE).text
    assert "B Yeni Ad" not in a.get(PAGE).text


def test_login_required(app):
    r = make_client(app).get(PAGE)
    assert r.status_code == 303
