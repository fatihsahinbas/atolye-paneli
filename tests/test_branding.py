"""Marka kuralları (PR #3): renkler tek yerde, logo ve ürün adı tek kaynaktan."""
import re
from pathlib import Path

from tests.conftest import make_client

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
CSS = (STATIC / "css" / "app.css").read_text(encoding="utf-8")
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _root_block() -> str:
    start = CSS.index(":root {")
    return CSS[start : CSS.index("}", start)]


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _palette() -> dict[str, str]:
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", _root_block()))


def test_no_hex_colors_outside_root():
    outside = CSS.replace(_root_block(), "")
    assert HEX.findall(outside) == []


def test_text_colors_meet_wcag_aa():
    p = _palette()
    pairs = [
        ("ink", "bg"), ("muted", "card"), ("muted", "surface-2"), ("brand", "card"),
        ("card", "brand"), ("ok", "ok-bg"), ("warn", "card"), ("bad", "bad-bg"),
        ("bad", "bad-bg-2"), ("card", "bad"), ("brand-2", "ink"), ("on-dark", "ink"),
    ]
    low = {f"{a}/{b}": round(_contrast(p[a], p[b]), 2) for a, b in pairs if _contrast(p[a], p[b]) < 4.5}
    assert low == {}


def test_inter_font_files_exist():
    for name in ("inter-latin-wght-normal.woff2", "inter-latin-ext-wght-normal.woff2", "OFL-Inter.txt"):
        assert (STATIC / "fonts" / name).is_file(), name
    assert "latin-ext" in CSS


def test_logo_and_app_name_on_login_page(app):
    r = make_client(app).get("/giris")
    assert r.status_code == 200
    assert '/static/img/logo.svg' in r.text
    assert 'rel="icon"' in r.text
    assert "◆" not in r.text
    assert "Atölye Paneli" in r.text  # APP_NAME varsayılanı


def test_logo_is_served(app):
    r = make_client(app).get("/static/img/logo.svg")
    assert r.status_code == 200
