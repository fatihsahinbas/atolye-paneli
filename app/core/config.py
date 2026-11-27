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

    # Bildirim kanalı: console | sms | whatsapp (PROJE 5 · Deha)
    # Anahtarlar yalnızca .env'den gelir; repr=False → log/hata çıktısında görünmez.
    notify_channel: str = "console"
    sms_api_url: str = ""
    sms_api_key: str = Field(default="", repr=False)
    whatsapp_api_url: str = ""
    whatsapp_api_key: str = Field(default="", repr=False)

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_from: str = ""
    smtp_user: str = ""
    smtp_password: str = Field(default="", repr=False)
    smtp_starttls: bool = True

    # Abonelik ödemesi (Hasan H4): fake | iyzico | paytr. Canlı ödeme kilidi: PAYMENT_LIVE=false
    payment_provider: str = "fake"
    payment_live: bool = False
    iyzico_api_key: str = Field(default="", repr=False)
    iyzico_secret_key: str = Field(default="", repr=False)
    iyzico_base_url: str = "https://sandbox-api.iyzipay.com"
    paytr_merchant_id: str = ""
    paytr_merchant_key: str = Field(default="", repr=False)
    paytr_merchant_salt: str = Field(default="", repr=False)
    paytr_test_mode: int = 1
    public_base_url: str = ""  # ödeme dönüş adresleri için (ör. https://panel.ornek.com); boşsa istekten

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
