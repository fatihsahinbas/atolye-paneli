"""Uygulama ayarları. Tüm gizli bilgiler .env / ortam değişkeninden gelir (Checklist #1)."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Atölye Paneli"
    env: str = "dev"  # dev | test | prod
    database_url: str = "sqlite:///./var/atolye.db"

    # Varsayılanı YOK: .env'de tanımlanmazsa uygulama açılmaz.
    secret_key: str = Field(min_length=32)

    cookie_secure: bool = True  # yalnızca lokal geliştirmede False
    session_ttl_hours: int = 12
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]

    media_root: str = "./var/media"
    max_upload_mb: int = 5

    payment_webhook_secret: str = ""  # boşsa webhook kapalı
    webhook_tolerance_sec: int = 300

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_from: str = ""
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True

    login_rate_limit: int = 5
    login_rate_window_sec: int = 900

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
