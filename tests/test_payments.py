"""H4 PROJE 1 · Abonelik ödemesi: Fake / iyzico / PayTR adaptörleri."""
import base64
import hashlib
import hmac
import io
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from app.core.deps import as_aware
from app.main import create_app
from app.modules.auth.models import Role, User
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.providers import IyzicoProvider, PaytrProvider, build_provider
from app.modules.workshop.models import Workshop
from tests.conftest import csrf, make_client, register

KEY, SALT = "paytr-key-123", "paytr-salt-456"


def _ws(app, slug="atolye-a") -> Workshop:
    with app.state.SessionLocal() as db:
        return db.query(Workshop).filter_by(slug=slug).one()


def _payments(app) -> list[Payment]:
    with app.state.SessionLocal() as db:
        return db.query(Payment).order_by(Payment.id).all()


def _start(c, plan="ATOLYE"):
    return c.post("/abonelik/baslat", data={"csrf_token": csrf(c, "/abonelik"), "plan_code": plan})


# --- Fake akış --------------------------------------------------------------------


def test_new_registration_has_14_day_trial(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    ends = as_aware(_ws(app).subscription_ends_at)
    assert abs(ends - (datetime.now(UTC) + timedelta(days=14))) < timedelta(minutes=1)


def test_fake_flow_pending_then_paid_extends_one_month(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    before = as_aware(_ws(app).subscription_ends_at)
    r = _start(c)
    assert r.status_code == 303
    p = _payments(app)[0]
    assert p.status == PaymentStatus.PENDING and p.amount == Decimal("950.00")
    assert r.headers["location"] == f"/odeme/test/{p.merchant_oid}"
    assert p.merchant_oid.isalnum()

    r = c.post(f"/odeme/test/{p.merchant_oid}", data={"csrf_token": csrf(c, "/abonelik"), "sonuc": "ok"})
    assert r.headers["location"] == "/abonelik?sonuc=ok"
    ws = _ws(app)
    assert _payments(app)[0].status == PaymentStatus.PAID
    assert ws.plan_code == "ATOLYE"
    after = as_aware(ws.subscription_ends_at)
    assert after.month != before.month or after.year != before.year  # bitiş tarihinden +1 ay

    # aynı sonuç ikinci kez → değişmez
    c.post(f"/odeme/test/{p.merchant_oid}", data={"csrf_token": csrf(c, "/abonelik"), "sonuc": "ok"})
    assert as_aware(_ws(app).subscription_ends_at) == after


def test_failed_fake_payment_keeps_subscription(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    before = _ws(app).subscription_ends_at
    _start(c)
    p = _payments(app)[0]
    c.post(f"/odeme/test/{p.merchant_oid}", data={"csrf_token": csrf(c, "/abonelik"), "sonuc": "hata"})
    assert _payments(app)[0].status == PaymentStatus.FAILED
    assert _ws(app).subscription_ends_at == before


def test_free_or_unknown_plan_rejected(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    assert _start(c, "PILOT").status_code == 400
    assert _start(c, "YOK").status_code == 400
    assert _payments(app) == []


def test_staff_cannot_start_payment(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    t = csrf(c, "/abonelik")
    with app.state.SessionLocal() as db:
        db.query(User).filter_by(email="a@ornek.com").one().role = Role.STAFF
        db.commit()
    assert c.post("/abonelik/baslat", data={"csrf_token": t, "plan_code": "ATOLYE"}).status_code == 403
    assert c.get("/abonelik").status_code == 403


def test_pilot_sees_no_pay_button(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    with app.state.SessionLocal() as db:
        db.query(Workshop).filter_by(slug="atolye-a").one().is_pilot = True
        db.commit()
    html = c.get("/abonelik").text
    assert "Pilot programı: ücretsiz" in html
    assert "/abonelik/baslat" not in html
    assert _start(c).status_code == 400


def test_other_workshop_payments_hidden(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@ornek.com")
    register(b, "atolye-b", "b@ornek.com")
    _start(a)
    oid = _payments(app)[0].merchant_oid
    assert "ATOLYE" not in b.get("/abonelik").text.split("Son ödemeler")[1]
    assert b.get(f"/odeme/test/{oid}").status_code == 404


def test_expired_subscription_shows_banner(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    assert "süreniz doldu" not in c.get("/").text
    with app.state.SessionLocal() as db:
        db.query(Workshop).filter_by(slug="atolye-a").one().subscription_ends_at = datetime(2020, 1, 1)  # naive
        db.commit()
    assert "süreniz doldu" in c.get("/").text


# --- PayTR ------------------------------------------------------------------------


def _paytr_app(settings, notifier):
    def handler(req: httpx.Request):
        return httpx.Response(200, json={"status": "success", "token": "tok123"})
    provider = PaytrProvider("m1", KEY, SALT, 1, client=httpx.Client(transport=httpx.MockTransport(handler)))
    return create_app(settings, notifier, payment_provider=provider)


def _paytr_hash(oid, status, total):
    digest = hmac.new(KEY.encode(), f"{oid}{SALT}{status}{total}".encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def test_paytr_wrong_hash_400_and_right_hash_ok(settings, notifier):
    app = _paytr_app(settings, notifier)
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    r = _start(c)
    assert r.status_code == 200 and "https://www.paytr.com/odeme/guvenli/tok123" in r.text
    p = _payments(app)[0]
    form = {"merchant_oid": p.merchant_oid, "status": "success", "total_amount": "95000", "hash": "yanlis"}
    pub = make_client(app)
    assert pub.post("/odeme/paytr/bildirim", data=form).status_code == 400
    assert _payments(app)[0].status == PaymentStatus.PENDING
    form["hash"] = _paytr_hash(p.merchant_oid, "success", "95000")
    r = pub.post("/odeme/paytr/bildirim", data=form)
    assert r.status_code == 200 and r.text == "OK"
    assert _payments(app)[0].status == PaymentStatus.PAID  # 95000 kuruş = 950,00 TL


def test_paytr_amount_mismatch_fails(settings, notifier):
    app = _paytr_app(settings, notifier)
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    before = _ws(app).subscription_ends_at
    _start(c)
    p = _payments(app)[0]
    form = {"merchant_oid": p.merchant_oid, "status": "success", "total_amount": "100",
            "hash": _paytr_hash(p.merchant_oid, "success", "100")}
    assert make_client(app).post("/odeme/paytr/bildirim", data=form).text == "OK"
    assert _payments(app)[0].status == PaymentStatus.FAILED
    assert _ws(app).subscription_ends_at == before


# --- iyzico (sahte SDK) -----------------------------------------------------------


class FakeIyzipay:
    payment_status = "SUCCESS"
    paid = "950.00"

    class CheckoutFormInitialize:
        def create(self, payload, options):
            FakeIyzipay.last = payload
            return io.BytesIO(json.dumps({"status": "success", "token": "iyz-tok",
                                          "paymentPageUrl": "https://sandbox-cpp.iyzipay.com/?token=iyz-tok"}).encode())

    class CheckoutForm:
        def retrieve(self, payload, options):
            return io.BytesIO(json.dumps({"status": "success", "paymentStatus": FakeIyzipay.payment_status,
                                          "paidPrice": FakeIyzipay.paid, "basketId": "x"}).encode())


@pytest.mark.parametrize(
    ("pay_status", "expected"), [("SUCCESS", PaymentStatus.PAID), ("FAILURE", PaymentStatus.FAILED)]
)
def test_iyzico_return_cookieless(settings, notifier, pay_status, expected):
    FakeIyzipay.payment_status = pay_status
    provider = IyzicoProvider("k", "s", "https://sandbox-api.iyzipay.com", sdk=FakeIyzipay)
    app = create_app(settings, notifier, payment_provider=provider)
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    r = _start(c)
    assert r.headers["location"].startswith("https://sandbox-cpp.iyzipay.com")
    assert FakeIyzipay.last["buyer"]["identityNumber"] == "11111111111"
    # Dönüş çerezsiz gelir (yeni istemci)
    r = make_client(app).post("/odeme/iyzico/donus", data={"token": "iyz-tok"})
    assert r.status_code == 303
    assert _payments(app)[0].status == expected


# --- Ayarlar ve kilit -------------------------------------------------------------


def test_live_lock_blocks_startup(settings, notifier):
    bad = settings.model_copy(update={"payment_provider": "paytr", "paytr_test_mode": 0, "paytr_merchant_id": "m",
                                      "paytr_merchant_key": "k", "paytr_merchant_salt": "s"})
    with pytest.raises(RuntimeError):
        create_app(bad, notifier)
    bad = settings.model_copy(update={"payment_provider": "iyzico", "iyzico_base_url": "https://api.iyzipay.com",
                                      "iyzico_api_key": "k", "iyzico_secret_key": "s"})
    with pytest.raises(RuntimeError):
        build_provider(bad)


def test_keys_not_in_repr_or_logs(settings, caplog, monkeypatch):
    s = settings.model_copy(update={"paytr_merchant_key": "SIRLI-ANAHTAR", "iyzico_secret_key": "IYZ-SIR"})
    assert "SIRLI-ANAHTAR" not in repr(s) and "IYZ-SIR" not in repr(s)
    p = PaytrProvider("m1", "SIRLI-ANAHTAR", "TUZ", 1)
    assert "SIRLI-ANAHTAR" not in repr(p) and "TUZ" not in repr(p)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(Exception):  # noqa: B017
            p.verify_notification({"merchant_oid": "x", "hash": "y"})
    assert "SIRLI-ANAHTAR" not in caplog.text
