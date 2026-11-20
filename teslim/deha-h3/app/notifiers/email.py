import smtplib
from email.message import EmailMessage

from app.notifiers.base import BaseNotifier


class EmailNotifier(BaseNotifier):
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        smtp_factory=smtplib.SMTP,
    ):
        self.host = host
        self.port = port
        self.user = user
        self._password = password
        self.sender = sender
        self.smtp_factory = smtp_factory

    def __repr__(self) -> str:
        return f"<EmailNotifier user={self.user} password=***>"

    def send(self, recipient: str, message: str) -> bool:
        msg = EmailMessage()
        msg["Subject"] = "Atölye Bildirimi"
        msg["From"] = self.sender
        msg["To"] = recipient
        msg.set_content(message)

        with self.smtp_factory(self.host, self.port) as server:
            server.starttls()
            server.login(self.user, self._password)
            server.send_message(msg)
        return True