"""Atölye ayarları formu.  Sahip: Seher"""
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.notifications.service import normalize_phone


class WorkshopSettingsIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if not v:
            return None  # boş telefon = vitrinde WhatsApp butonu yok
        return normalize_phone(v)  # ValueError → "Geçersiz telefon numarası"
