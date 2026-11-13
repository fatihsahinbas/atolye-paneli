"""PROJE 5 · SMS / WhatsApp adaptörü testleri (Deha). Gerçek ağ YOK: httpx.MockTransport."""
import json
import logging

import httpx
import pytest
from sqlalchemy import select

from app.main import create_app
from app.modules.notifications.models import Notification, NotificationStatus
from app.modules.notifications.service import (
    ConsoleNotifier,
    SmsNotifier,
    WhatsAppNotifier,
    build_notifier,
    normalize_phone,
)
from tests.conftest import csrf, make_client, register, seed_order

SECRET = "super-secret-api-key-12345"


class Recorder:
    """Sahte sağlayıcı: gelen istekleri saklar, verilen durum kodunu döner."""

    def __init__(self, status: int = 200, error: Exception | None = None) -> None:
        self.status, self.error = status, error
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.error:
            raise self.error
        return httpx.Response(self.status)

    @property
    def last_json(self) -> dict:
        return json.loads(self.requests[-1].content)


def sms(recorder: Recorder, api_key: str = SECRET) -> SmsNotifier:
    client = httpx.Client(transport=httpx.MockTransport(recorder))
    return SmsNotifier(api_url="https://sms.fake.local/send", api_key=api_key, client=client)


def run_status_change(settings, notifier, consent: bool = True) -> tuple[Notification, str]:
    """Kayıt → sipariş → 'Üretimde' geçişi. (son bildirim, sipariş sayfası) döner."""
    app = create_app(settings, notifier)
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c, consent=consent)
    r = c.post(f"/siparisler/{oid}/durum", data={"csrf_token": csrf(c), "to_status": "IN_PRODUCTION"})
    assert r.status_code == 303
    with app.state.SessionLocal() as db:
        n = db.scalars(select(Notification).order_by(Notification.id.desc())).first()
    return n, c.get(f"/siparisler/{oid}").text


# --- Uçtan uca: sipariş durumu → sağlayıcı ------------------------------------


def test_provider_200_marks_sent_with_e164_phone(settings):
    rec = Recorder(200)
    n, _ = run_status_change(settings, sms(rec))
    assert n.status == NotificationStatus.SENT and n.channel == "sms"
    assert len(rec.requests) == 1
    assert rec.last_json["to"] == "+905321112233"  # müşteri "0532 111 22 33" girdi
    assert "Mehmet" in rec.last_json["message"]
    assert rec.requests[0].headers["authorization"] == f"Bearer {SECRET}"


def test_provider_500_marks_failed_but_order_status_changes(settings):
    n, page = run_status_change(settings, sms(Recorder(500)))
    assert n.status == NotificationStatus.FAILED
    assert "Üretimde" in page  # sağlayıcı çöktü, atölyenin işi durmadı


def test_provider_unreachable_marks_failed(settings):
    n, page = run_status_change(settings, sms(Recorder(error=httpx.ConnectError("bağlantı yok"))))
    assert n.status == NotificationStatus.FAILED
    assert "Üretimde" in page


def test_no_consent_skips_without_request(settings):
    rec = Recorder(200)
    n, _ = run_status_change(settings, sms(rec), consent=False)
    assert n.status == NotificationStatus.SKIPPED
    assert rec.requests == [], "Rıza yokken sağlayıcıya istek atılmamalı"


def test_api_key_not_leaked(settings, caplog, monkeypatch):
    # setup_logging() root handler'larını değiştirir ve caplog'u siler; bu testte kapat.
    monkeypatch.setattr("app.main.setup_logging", lambda: None)
    caplog.set_level(logging.DEBUG)
    notifier = sms(Recorder(500))  # hata üret ki log tetiklensin
    run_status_change(settings, notifier)
    assert "Bildirim gönderilemedi" in caplog.text
    assert SECRET not in caplog.text
    assert SECRET not in repr(notifier)
    s = settings.model_copy(update={"notify_channel": "sms", "sms_api_url": "https://x", "sms_api_key": SECRET})
    assert SECRET not in repr(s)


# --- Birim: telefon, fabrika, WhatsApp gövdesi -------------------------------


@pytest.mark.parametrize("raw", ["0532 111 22 33", "+90 532 111 22 33", "905321112233", "532 111 22 33",
                                 "(0532) 111-22-33"])
def test_normalize_phone_variants(raw):
    assert normalize_phone(raw) == "+905321112233"


@pytest.mark.parametrize("raw", ["", "12345", "0532 111 22 33 44"])
def test_normalize_phone_rejects_invalid(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


def test_build_notifier_by_channel(settings):
    assert isinstance(build_notifier(settings), ConsoleNotifier)  # varsayılan
    s = settings.model_copy(update={"notify_channel": "SMS", "sms_api_url": "https://x", "sms_api_key": "k"})
    assert isinstance(build_notifier(s), SmsNotifier)
    w = settings.model_copy(update={"notify_channel": "whatsapp", "whatsapp_api_url": "https://x",
                                    "whatsapp_api_key": "k"})
    assert isinstance(build_notifier(w), WhatsAppNotifier)


def test_build_notifier_requires_credentials(settings):
    s = settings.model_copy(update={"notify_channel": "sms"})
    with pytest.raises(ValueError, match="api_url ve api_key"):
        build_notifier(s)


def test_build_notifier_unknown_channel(settings):
    with pytest.raises(ValueError, match="Bilinmeyen"):
        build_notifier(settings.model_copy(update={"notify_channel": "guvercin"}))


def test_whatsapp_body_format():
    rec = Recorder(200)
    client = httpx.Client(transport=httpx.MockTransport(rec))
    WhatsAppNotifier("https://wa.fake.local/messages", "k", client=client).send("0532 111 22 33", "Merhaba")
    assert rec.last_json == {"messaging_product": "whatsapp", "to": "905321112233", "type": "text",
                             "text": {"body": "Merhaba"}}
