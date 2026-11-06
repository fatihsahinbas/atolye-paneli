"""Güvenli dosya yükleme (Checklist #7).  Sahip: Alper

- Boyut sınırı (akış halinde okunur, sınır aşılınca kesilir)
- Uzantıya DEĞİL dosyanın ilk byte'larına (magic bytes) bakılır
- Dosya adı uuid ile yeniden üretilir, web kökü dışına kaydedilir
- Görsel Pillow ile doğrulanır, yönü düzeltilir ve EXIF'siz yeniden kodlanır (GPS konumu sızmaz)
- Her görselden en fazla 400 px küçük resim üretilir: {uuid}_t.webp
"""
import uuid
import warnings
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

from app.modules.media.models import Media

CHUNK = 64 * 1024
THUMB_PX = 400
Image.MAX_IMAGE_PIXELS = 40_000_000  # dev boyutlu "bomba" görsellere sınır

_FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


class UploadError(ValueError):
    pass


def sniff_image(head: bytes) -> tuple[str, str] | None:
    """(content_type, uzantı) veya None."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def thumb_name(stored_name: str) -> str:
    """Küçük resmin adı orijinalden türetilir (migration gerekmez)."""
    return f"{Path(stored_name).stem}_t.webp"


def _decode(data: bytes) -> Image.Image:
    """Doğrulanmış, yönü düzeltilmiş görsel. Bozuk/sahte/aşırı büyük → UploadError."""
    try:
        with warnings.catch_warnings():
            # MAX_IMAGE_PIXELS aşımı normalde yalnızca uyarıdır; hataya çevir
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                probe.verify()
            img = Image.open(BytesIO(data))  # verify() sonrası nesne kullanılamaz, yeniden aç
            img.load()  # verify() piksel verisini çözmez; yarım kalmış dosya burada yakalanır
            return ImageOps.exif_transpose(img)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise UploadError("Görselin çözünürlüğü çok büyük") from e
    except Exception as e:  # Pillow bozuk veride çok çeşitli hatalar fırlatır; hiçbiri 500 olmamalı
        raise UploadError("Görsel bozuk ya da okunamıyor") from e


def _encode(img: Image.Image, fmt: str) -> bytes:
    """Meta verisiz (EXIF, XMP, yorum) yeniden kodlar; renk profili (ICC) korunur."""
    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif fmt == "WEBP" and img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if img.has_transparency_data else "RGB")
    opts: dict = {"exif": b"", "comment": b""}
    if icc := img.info.get("icc_profile"):
        opts["icc_profile"] = icc
    if fmt in ("JPEG", "WEBP"):
        opts["quality"] = 85
    buf = BytesIO()
    img.save(buf, format=fmt, **opts)
    return buf.getvalue()


async def save_image(file: UploadFile, media_root: str, max_bytes: int) -> tuple[str, str, int]:
    """(stored_name, content_type, size) döner. Yanında küçük resim de kaydedilir."""
    data = bytearray()
    while chunk := await file.read(CHUNK):
        data.extend(chunk)
        if len(data) > max_bytes:
            raise UploadError(f"Dosya en fazla {max_bytes // (1024 * 1024)} MB olabilir")
    if not data:
        raise UploadError("Dosya boş")
    kind = sniff_image(bytes(data[:16]))
    if kind is None:
        raise UploadError("Yalnızca JPEG, PNG veya WEBP yüklenebilir")
    content_type, ext = kind
    img = _decode(bytes(data))
    original = _encode(img, _FORMATS[content_type])
    thumb = img.copy()
    thumb.thumbnail((THUMB_PX, THUMB_PX))
    stored_name = f"{uuid.uuid4().hex}{ext}"
    root = Path(media_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / stored_name).write_bytes(original)
    (root / thumb_name(stored_name)).write_bytes(_encode(thumb, "WEBP"))
    return stored_name, content_type, len(original)


def media_path(media_root: str, stored_name: str) -> Path:
    # stored_name sadece bizim ürettiğimiz uuid; yine de path traversal'a karşı kontrol
    p = (Path(media_root) / stored_name).resolve()
    if p.parent != Path(media_root).resolve():
        raise UploadError("Geçersiz yol")
    return p


def media_response(media_root: str, m: Media, boyut: str | None) -> FileResponse:
    """`boyut=kucuk` → küçük resim; küçük resmi olmayan eski yüklemelerde orijinal."""
    if boyut == "kucuk":
        p = media_path(media_root, thumb_name(m.stored_name))
        if p.exists():
            return FileResponse(p, media_type="image/webp")
    return FileResponse(media_path(media_root, m.stored_name), media_type=m.content_type)
