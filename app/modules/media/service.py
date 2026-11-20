
"""Güvenli dosya yükleme (Checklist #7)."""
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

Image.MAX_IMAGE_PIXELS = 40_000_000

_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


class UploadError(ValueError):
    pass


def sniff_image(head: bytes) -> tuple[str, str] | None:
    """Dosyanın ilk byte değerlerinden görsel türünü belirler."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"

    if (
        len(head) >= 12
        and head[:4] == b"RIFF"
        and head[8:12] == b"WEBP"
    ):
        return "image/webp", ".webp"

    return None


def thumb_name(stored_name: str) -> str:
    """Küçük resmin dosya adını üretir."""
    return f"{Path(stored_name).stem}_t.webp"


def _decode(data: bytes) -> Image.Image:
    """Görseli doğrular ve EXIF yönünü uygular."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            with Image.open(BytesIO(data)) as probe:
                probe.verify()

            with Image.open(BytesIO(data)) as img:
                img.load()
                corrected = ImageOps.exif_transpose(img)
                corrected.load()
                return corrected.copy()

    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise UploadError(
            "Görselin çözünürlüğü çok büyük"
        ) from exc

    except Exception as exc:
        raise UploadError(
            "Görsel bozuk ya da okunamıyor"
        ) from exc


def _encode(img: Image.Image, fmt: str) -> bytes:
    """EXIF ve diğer metadata bilgilerini temizleyerek kaydeder."""

    if fmt == "JPEG":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

    elif fmt == "WEBP":
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

    opts = {
        "exif": b"",
        "comment": b"",
    }

    icc_profile = img.info.get("icc_profile")
    if icc_profile:
        opts["icc_profile"] = icc_profile

    if fmt in ("JPEG", "WEBP"):
        opts["quality"] = 85

    buffer = BytesIO()
    img.save(buffer, format=fmt, **opts)

    return buffer.getvalue()


async def save_image(
    file: UploadFile,
    media_root: str,
    max_bytes: int,
) -> tuple[str, str, int]:
    """Orijinal görseli ve en fazla 400 px WEBP küçük resmi kaydeder."""

    data = bytearray()

    while True:
        chunk = await file.read(CHUNK)

        if not chunk:
            break

        data.extend(chunk)

        if len(data) > max_bytes:
            raise UploadError(
                f"Dosya en fazla {max_bytes // (1024 * 1024)} MB olabilir"
            )

    if not data:
        raise UploadError("Dosya boş")

    kind = sniff_image(bytes(data[:16]))

    if kind is None:
        raise UploadError(
            "Yalnızca JPEG, PNG veya WEBP yüklenebilir"
        )

    content_type, ext = kind

    img = _decode(bytes(data))

    # Orijinal görselin EXIF temizlenmiş hali.
    original = _encode(img, _FORMATS[content_type])

    # Küçük resim için orijinalin kopyası.
    thumb = img.copy()

    # En-boy oranını koruyarak maksimum 400x400.
    thumb.thumbnail(
        (THUMB_PX, THUMB_PX),
        Image.Resampling.LANCZOS,
    )

    # Küçük resmi mutlaka WEBP olarak kodla.
    thumb_data = _encode(thumb, "WEBP")

    stored_name = f"{uuid.uuid4().hex}{ext}"

    root = Path(media_root)
    root.mkdir(parents=True, exist_ok=True)

    original_path = root / stored_name
    thumbnail_path = root / thumb_name(stored_name)

    try:
        original_path.write_bytes(original)
        thumbnail_path.write_bytes(thumb_data)

    except OSError as exc:
        original_path.unlink(missing_ok=True)
        thumbnail_path.unlink(missing_ok=True)
        raise UploadError(
            "Görsel diske kaydedilemedi"
        ) from exc

    return stored_name, content_type, len(original)


def media_path(media_root: str, stored_name: str) -> Path:
    """Dosyanın medya klasörü dışına çıkmasını engeller."""

    root = Path(media_root).resolve()
    path = (root / stored_name).resolve()

    if path.parent != root:
        raise UploadError("Geçersiz yol")

    return path


def media_response(
    media_root: str,
    m: Media,
    boyut: str | None,
) -> FileResponse:
    """Küçük resim istenirse WEBP dosyasını döndürür."""

    if boyut == "kucuk":
        thumbnail = media_path(
            media_root,
            thumb_name(m.stored_name),
        )

        if thumbnail.is_file():
            return FileResponse(
                thumbnail,
                media_type="image/webp",
            )

    return FileResponse(
        media_path(media_root, m.stored_name),
        media_type=m.content_type,
    )
