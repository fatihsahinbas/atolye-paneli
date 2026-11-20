"""Şifre sıfırlama e-postası. SMTP ayarı yoksa yalnızca test ortamında taklit edilir."""
import smtplib
from email.message import EmailMessage

from app.core.config import Settings


def send_reset_email(settings: Settings, to_email: str, url: str) -> None:
    if not all((settings.smtp_host, settings.smtp_from)):
        raise RuntimeError("SMTP_HOST ve SMTP_FROM yapılandırılmalı")
    msg = EmailMessage()
    msg["Subject"] = "Atölye Paneli - Şifre sıfırlama"
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(
        "Şifrenizi sıfırlamak için aşağıdaki bağlantıyı 30 dakika içinde açın:\n"
        f"{url}\n\nBu işlemi istemediyseniz e-postayı dikkate almayın."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
