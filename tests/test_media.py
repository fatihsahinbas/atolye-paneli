"""Küçük resim + EXIF temizleme (H2 · PROJE 6)."""
import io
import re
from pathlib import Path

import pytest
from PIL import ExifTags, Image

from tests.conftest import csrf, make_client, make_image, register, seed_order


def phone_jpeg(size: tuple[int, int] = (600, 300), orientation: int = 1) -> bytes:
    """İçinde GPS konumu ve yön bilgisi olan, telefondan çekilmiş gibi bir JPEG."""
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "TestPhone"
    exif[ExifTags.Base.Orientation] = orientation
    exif[ExifTags.IFD.GPSInfo] = {
        ExifTags.GPS.GPSLatitudeRef: "N",
        ExifTags.GPS.GPSLatitude: (41.0, 2.0, 30.0),
        ExifTags.GPS.GPSLongitudeRef: "E",
        ExifTags.GPS.GPSLongitude: (28.0, 58.0, 10.0),
    }
    return make_image(size, "JPEG", exif=exif)


def open_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


@pytest.fixture
def client(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    return c


def upload(c, oid: int, data: bytes, name: str = "foto.jpg", ctype: str = "image/jpeg"):
    return c.post(f"/siparisler/{oid}/medya", data={"csrf_token": csrf(c), "is_public": "true"},
                  files={"file": (name, io.BytesIO(data), ctype)})


def last_media_id(c, oid: int) -> str:
    return re.findall(r'href="/medya/(\d+)"', c.get(f"/siparisler/{oid}").text)[-1]


def test_gps_exif_is_removed(client, settings):
    src = phone_jpeg()
    assert open_image(src).getexif().get_ifd(ExifTags.IFD.GPSInfo), "test görselinde GPS olmalı"
    oid = seed_order(client)
    assert upload(client, oid, src).status_code == 303
    mid = last_media_id(client, oid)

    for url in (f"/medya/{mid}", f"/medya/{mid}?boyut=kucuk"):
        body = client.get(url).content
        assert not open_image(body).getexif(), f"{url} EXIF taşımamalı"
        assert b"Exif" not in body
    # Diskte de EXIF'li kopya kalmamalı
    for f in Path(settings.media_root).iterdir():
        assert not open_image(f.read_bytes()).getexif(), f.name


def test_thumbnail_is_at_most_400px_and_shown_in_gallery(client, settings):
    oid = seed_order(client)
    assert upload(client, oid, make_image((3000, 2000), "JPEG")).status_code == 303
    mid = last_media_id(client, oid)

    detail = client.get(f"/siparisler/{oid}").text
    assert f'src="/medya/{mid}?boyut=kucuk"' in detail  # galeri küçük resmi gösterir
    r = client.get(f"/medya/{mid}?boyut=kucuk")
    assert r.headers["content-type"] == "image/webp"
    assert open_image(r.content).size == (400, 267)
    assert open_image(client.get(f"/medya/{mid}").content).size == (3000, 2000)  # orijinal korunur
    assert sorted(p.suffix for p in Path(settings.media_root).iterdir()) == [".jpg", ".webp"]


def test_public_tracking_page_serves_thumbnail(client, app):
    oid = seed_order(client)
    upload(client, oid, make_image((1200, 900), "PNG"), "kalip.png", "image/png")
    mid = last_media_id(client, oid)
    code = re.search(r"/t/([\w-]+)</code>", client.get(f"/siparisler/{oid}").text).group(1)

    public = make_client(app)
    assert f'src="/t/{code}/medya/{mid}?boyut=kucuk"' in public.get(f"/t/{code}").text
    r = public.get(f"/t/{code}/medya/{mid}?boyut=kucuk")
    assert r.status_code == 200
    assert max(open_image(r.content).size) == 400


def test_phone_orientation_is_applied(client):
    # 600x300 kaydedilmiş ama EXIF "90° döndür" diyor (Orientation=6) → dik fotoğraf
    oid = seed_order(client)
    assert upload(client, oid, phone_jpeg((600, 300), orientation=6)).status_code == 303
    mid = last_media_id(client, oid)
    assert open_image(client.get(f"/medya/{mid}").content).size == (300, 600)
    assert open_image(client.get(f"/medya/{mid}?boyut=kucuk").content).size == (200, 400)


@pytest.mark.parametrize("data, name, ctype", [
    (b"\xff\xd8\xff" + b"cop" * 200, "x.jpg", "image/jpeg"),                    # JPEG imzası, içi çöp
    (b"\x89PNG\r\n\x1a\n" + b"\x00" * 200, "x.png", "image/png"),               # PNG imzası, içi çöp
    (b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 100, "x.webp", "image/webp"),  # WEBP imzası, içi çöp
    (make_image((800, 600), "JPEG")[:400], "yarim.jpg", "image/jpeg"),          # yarıda kesilmiş dosya
])
def test_fake_or_broken_image_returns_400(client, settings, data, name, ctype):
    oid = seed_order(client)
    r = upload(client, oid, data, name, ctype)
    assert r.status_code == 400
    assert "bozuk" in r.text
    assert not Path(settings.media_root).exists() or not any(Path(settings.media_root).iterdir())


def test_decompression_bomb_is_rejected(client):
    buf = io.BytesIO()
    Image.new("1", (8000, 6000)).save(buf, "PNG")  # 48 MP ama dosyası küçük
    oid = seed_order(client)
    r = upload(client, oid, buf.getvalue(), "bomba.png", "image/png")
    assert r.status_code == 400
    assert "çözünürlüğü çok büyük" in r.text


def test_other_workshop_cannot_access_thumbnail(client, app):
    oid = seed_order(client)
    upload(client, oid, make_image((800, 600), "JPEG"))
    mid = last_media_id(client, oid)
    b = make_client(app)
    register(b, "atolye-b", "b@ornek.com")
    assert b.get(f"/medya/{mid}?boyut=kucuk").status_code == 404
