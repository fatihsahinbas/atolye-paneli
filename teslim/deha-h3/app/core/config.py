from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "noreply@localhost"
    database_url: str = "sqlite:///./atolye.db"
    secret_key: str = "change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()