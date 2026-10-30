"""Girdi doğrulama (Checklist #6). Tüm form girdileri Pydantic'ten geçer."""
import re

from pydantic import BaseModel, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,58})[a-z0-9]$")


def _email(v: str) -> str:
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("Geçerli bir e-posta girin")
    return v


class RegisterIn(BaseModel):
    workshop_name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=3, max_length=60)
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128)

    _norm_email = field_validator("email")(_email)

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not SLUG_RE.match(v):
            raise ValueError("Adres yalnızca küçük harf, rakam ve tire içerebilir")
        return v

    @field_validator("workshop_name", "full_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    _norm_email = field_validator("email")(_email)


def first_error(exc: Exception) -> str:
    """Pydantic hatasını kullanıcıya gösterilecek tek cümleye indirger."""
    errors = getattr(exc, "errors", None)
    if callable(errors):
        errs = errors()
        if errs:
            msg = str(errs[0].get("msg", "Geçersiz giriş"))
            return msg.removeprefix("Value error, ")
    return "Geçersiz giriş"
