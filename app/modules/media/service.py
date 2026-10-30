"""Güvenli dosya yükleme (Checklist #7).  Sahip: Alper

- Boyut sınırı (akış halinde okunur, sınır aşılınca kesilir)
- Uzantıya DEĞİL dosyanın ilk byte'larına (magic bytes) bakılır
- Dosya adı uuid ile yeniden üretilir, web kökü dışına kaydedilir
"""
import uuid
from pathlib import Path

from fastapi import UploadFile

CHUNK = 64 * 1024


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


async def save_image(file: UploadFile, media_root: str, max_bytes: int) -> tuple[str, str, int]:
    """(stored_name, content_type, size) döner."""
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
    stored_name = f"{uuid.uuid4().hex}{ext}"
    root = Path(media_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / stored_name).write_bytes(data)
    return stored_name, content_type, len(data)


def media_path(media_root: str, stored_name: str) -> Path:
    # stored_name sadece bizim ürettiğimiz uuid; yine de path traversal'a karşı kontrol
    p = (Path(media_root) / stored_name).resolve()
    if p.parent != Path(media_root).resolve():
        raise UploadError("Geçersiz yol")
    return p
