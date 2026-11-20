"""Vitrin /v/{slug} (PR #6, Seher): ürün kartları, detay modalı, WhatsApp butonu."""
import re
from pathlib import Path

from sqlalchemy import select

from app.modules.workshop.models import Workshop
from tests.conftest import csrf, make_client, register

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


def _setup(app, slug: str, product_name: str, phone: str | None = None):
    c = make_client(app)
    register(c, slug, f"{slug}@ornek.com")
    t = csrf(c)
    c.post("/urunler", data={"csrf_token": t, "name": product_name, "pricing_type": "FIXED",
                             "base_price": "1500", "show_in_showcase": "true"})
    if phone is not None:
        with app.state.SessionLocal() as db:
            ws = db.scalar(select(Workshop).where(Workshop.slug == slug))
            ws.phone = phone
            db.commit()
    return make_client(app)  # vitrin girişsiz açılır


def test_showcase_shows_own_product_name(app):
    _setup(app, "filo", "Filografi Tablo")
    _setup(app, "kuyum", "14 Ayar Kolye")
    html = make_client(app).get("/v/filo").text
    assert "Filografi Tablo" in html
    assert "14 Ayar Kolye" not in html  # başka atölyenin ürünü/adı sızmıyor
    assert 'data-modal-id="modal-1"' in html and 'id="modal-1"' in html


def test_whatsapp_button_uses_workshop_phone(app):
    _setup(app, "filo", "Filografi & Tablo", phone="0532 111 22 33")
    html = make_client(app).get("/v/filo").text
    link = re.search(r'href="(https://wa\.me/[^"]+)"', html).group(1)
    assert link.startswith("https://wa.me/905321112233?text=")
    assert "Filografi%20%26%20Tablo" in link
    assert "905555555555" not in html
    assert 'rel="noopener"' in html


def test_no_whatsapp_button_without_valid_phone(app):
    _setup(app, "filo", "Filografi Tablo")
    _setup(app, "bozuk", "Kolye", phone="123")
    assert "wa.me" not in make_client(app).get("/v/filo").text
    assert "wa.me" not in make_client(app).get("/v/bozuk").text


def test_showcase_is_csp_clean(app):
    _setup(app, "filo", "Filografi Tablo")
    html = make_client(app).get("/v/filo").text
    assert " style=" not in html
    assert "onclick" not in html
    assert re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html) == []  # yalnız harici script
    assert '/static/js/showcase.js' in html
    assert make_client(app).get("/static/js/showcase.js").status_code == 200


def test_order_form_script_not_overwritten():
    # Regresyon: PR #6'nın ilk sürümü app.js'i silip sipariş formu fiyat önizlemesini bozmuştu.
    app_js = (STATIC / "js" / "app.js").read_text(encoding="utf-8")
    assert "fiyat" in app_js
    assert "modal" not in (app_js.lower())
