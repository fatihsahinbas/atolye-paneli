"""H3 PROJE 6 · E-posta adaptörü + bildirim geçmişi."""
import logging

import pytest

from app.main import create_app
from app.modules.customers.models import Customer
from app.modules.notifications.models import Notification, NotificationStatus
from app.modules.notifications.service import EmailNotifier
from tests.conftest import csrf, make_client, register, seed_order


class FakeSMTP:
    sent: list = []
    fail = False

    def __init__(self, host, port, timeout=10):
        self.host = host

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        if FakeSMTP.fail:
            raise OSError("smtp down")
        FakeSMTP.sent.append(msg)


@pytest.fixture
def mail_app(settings, notifier):
    FakeSMTP.sent, FakeSMTP.fail = [], False
    email = EmailNotifier("smtp.ornek.com", 587, "u", "gizli-sifre", "atolye@ornek.com", smtp_factory=FakeSMTP)
    return create_app(settings, notifier, email)


def _email_only_customer(app):
    with app.state.SessionLocal() as db:
        c = db.query(Customer).one()
        c.phone, c.email = None, "musteri@ornek.com"
        db.commit()


def _move(c, oid, to="IN_PRODUCTION"):
    return c.post(f"/siparisler/{oid}/durum", data={"csrf_token": csrf(c), "to_status": to})


def _last(app) -> Notification:
    with app.state.SessionLocal() as db:
        return db.query(Notification).order_by(Notification.id.desc()).first()


def test_no_phone_uses_email(mail_app, notifier):
    c = make_client(mail_app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    _email_only_customer(mail_app)
    _move(c, oid)
    n = _last(mail_app)
    assert (n.channel, n.status, n.recipient) == ("email", NotificationStatus.SENT, "musteri@ornek.com")
    assert FakeSMTP.sent[0]["To"] == "musteri@ornek.com"
    assert notifier.sent == []


def test_smtp_failure_marks_failed_but_status_changes_then_retry(mail_app):
    c = make_client(mail_app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    _email_only_customer(mail_app)
    FakeSMTP.fail = True
    _move(c, oid)
    n = _last(mail_app)
    assert n.status == NotificationStatus.FAILED
    html = c.get(f"/siparisler/{oid}").text
    assert "Gönderilen bildirimler" in html and f"/bildirimler/{n.id}/tekrar" in html

    FakeSMTP.fail = False
    r = c.post(f"/bildirimler/{n.id}/tekrar", data={"csrf_token": csrf(c)})
    assert r.status_code == 303
    assert _last(mail_app).status == NotificationStatus.SENT
    # SENT kayıt tekrar gönderilmez
    c.post(f"/bildirimler/{n.id}/tekrar", data={"csrf_token": csrf(c)})
    assert len(FakeSMTP.sent) == 1


def test_no_contact_is_skipped(mail_app):
    c = make_client(mail_app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    with mail_app.state.SessionLocal() as db:
        db.query(Customer).one().phone = None
        db.commit()
    _move(c, oid)
    assert _last(mail_app).status == NotificationStatus.SKIPPED


def test_other_workshop_retry_is_404(mail_app):
    a, b = make_client(mail_app), make_client(mail_app)
    register(a, "atolye-a", "a@ornek.com")
    register(b, "atolye-b", "b@ornek.com")
    oid = seed_order(a)
    _move(a, oid)
    n = _last(mail_app)
    assert b.post(f"/bildirimler/{n.id}/tekrar", data={"csrf_token": csrf(b)}).status_code == 404


def test_email_not_in_logs_and_password_not_in_repr(mail_app, caplog, monkeypatch):
    monkeypatch.setattr("app.main.setup_logging", lambda: None)
    c = make_client(mail_app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    _email_only_customer(mail_app)
    FakeSMTP.fail = True
    with caplog.at_level(logging.DEBUG):
        _move(c, oid)
    assert "musteri@ornek.com" not in caplog.text
    assert "gizli-sifre" not in repr(mail_app.state.email_notifier)
