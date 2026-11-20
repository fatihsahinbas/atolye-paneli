from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.logging import setup_logging
from app.database import Base, engine
from app.notifiers.email import EmailNotifier
from app.notifiers.sms import SmsNotifier
from app.notifiers.multi import MultiNotifier
from app.routes import orders, notifications

setup_logging()

app = FastAPI(title="AtolyeNotifier")
Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="app/templates")

# Uygulama genelinde notifier (test'te override edilebilir)
app.state.notifier = MultiNotifier(
    sms=SmsNotifier(),
    email=EmailNotifier(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password,
        sender=settings.mail_from,
    ),
)

app.include_router(orders.router)
app.include_router(notifications.router)


@app.get("/health")
def health():
    return {"ok": True}curl -s http://127.0.0.1:8000/health