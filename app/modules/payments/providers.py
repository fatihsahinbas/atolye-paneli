"""Ödeme sağlayıcı adaptörleri: Fake, iyzico (Checkout Form), PayTR (iFrame API).  Sahip: Hasan (H4)

Bir protokol, üç uygulama. Sağlayıcı değişince iş kodu (service.py) değişmez.
Kart bilgisine hiç dokunulmaz: ödeme formu sağlayıcının sayfasında açılır.
Doğrulama sağlayıcıya özeldir, protokolde yok:
  - iyzico: dönüşteki token ile sunucudan CheckoutForm.retrieve
  - PayTR:  bildirimdeki hash = base64(hmac_sha256(key, oid + salt + status + total_amount))
"""
import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.core.security import safe_equals

IYZICO_SANDBOX = "https://sandbox-api.iyzipay.com"
PAYTR_TOKEN_URL = "https://www.paytr.com/odeme/api/get-token"


class InvalidSignature(Exception):
    pass


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class CheckoutRequest:
    merchant_oid: str
    amount: Decimal
    description: str
    buyer_email: str
    buyer_name: str
    buyer_ip: str
    callback_url: str  # iyzico'nun tarayıcıyı döndüreceği adres
    ok_url: str        # PayTR başarı / hata sayfaları
    fail_url: str


@dataclass(frozen=True)
class CheckoutStart:
    redirect_url: str | None = None  # iyzico, fake
    iframe_url: str | None = None    # PayTR
    provider_ref: str = ""           # iyzico token (dönüşte Payment'ı bulmak için)


@dataclass(frozen=True)
class PaymentResult:
    merchant_oid: str
    success: bool
    amount: Decimal  # TL
    provider_ref: str = ""


class PaymentProvider(Protocol):
    name: str

    def start(self, req: CheckoutRequest) -> CheckoutStart: ...


def to_kurus(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def tl(amount: Decimal) -> str:
    """iyzico fiyat alanı: '199.00'"""
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class FakeProvider:
    """Testler ve anahtarsız demo: ödeme sayfası bizim /odeme/test/{oid} ekranımız."""

    name = "fake"

    def start(self, req: CheckoutRequest) -> CheckoutStart:
        return CheckoutStart(redirect_url=f"/odeme/test/{req.merchant_oid}", provider_ref=req.merchant_oid)


class IyzicoProvider:
    name = "iyzico"

    def __init__(self, api_key: str, secret_key: str, base_url: str, sdk: Any = None) -> None:
        if not api_key or not secret_key:
            raise ValueError("iyzico: IYZICO_API_KEY ve IYZICO_SECRET_KEY zorunlu")
        if sdk is None:
            import iyzipay as sdk  # noqa: PLC0415  yalnız iyzico seçiliyse yüklenir
        self._sdk = sdk
        host = base_url.removeprefix("https://").removeprefix("http://").rstrip("/")
        self._options = {"api_key": api_key, "secret_key": secret_key, "base_url": host}

    def __repr__(self) -> str:
        return f"IyzicoProvider(base_url={self._options['base_url']!r}, keys='***')"

    @staticmethod
    def _read(raw: Any) -> dict:
        body = raw.read().decode("utf-8") if hasattr(raw, "read") else raw
        return json.loads(body) if isinstance(body, str | bytes) else dict(body)

    def start(self, req: CheckoutRequest) -> CheckoutStart:
        name, _, surname = (req.buyer_name or "Atölye Sahibi").partition(" ")
        price = tl(req.amount)
        address = {"contactName": req.buyer_name, "city": "Istanbul", "country": "Turkey", "address": "Türkiye"}
        payload = {
            "locale": "tr",
            "conversationId": req.merchant_oid,
            "price": price,
            "paidPrice": price,
            "currency": "TRY",
            "basketId": req.merchant_oid,
            "paymentGroup": "SUBSCRIPTION",
            "callbackUrl": req.callback_url,
            "enabledInstallments": [1],
            "buyer": {
                "id": req.merchant_oid,
                "name": name,
                "surname": surname or "-",
                "email": req.buyer_email,
                "identityNumber": "11111111111",  # KVKK: TC kimlik sorulmaz (test ortamında yeterli)
                "registrationAddress": "Türkiye",
                "ip": req.buyer_ip,
                "city": "Istanbul",
                "country": "Turkey",
            },
            "shippingAddress": address,
            "billingAddress": address,
            "basketItems": [{
                "id": req.merchant_oid, "name": req.description, "category1": "Abonelik",
                "itemType": "VIRTUAL", "price": price,
            }],
        }
        data = self._read(self._sdk.CheckoutFormInitialize().create(payload, self._options))
        if data.get("status") != "success" or not data.get("paymentPageUrl"):
            raise ProviderError(f"iyzico başlatma hatası: {data.get('errorCode', '?')}")
        return CheckoutStart(redirect_url=data["paymentPageUrl"], provider_ref=data.get("token", ""))

    def retrieve(self, token: str) -> PaymentResult:
        data = self._read(self._sdk.CheckoutForm().retrieve({"locale": "tr", "token": token}, self._options))
        ok = data.get("status") == "success" and data.get("paymentStatus") == "SUCCESS"
        return PaymentResult(
            merchant_oid=str(data.get("basketId") or data.get("conversationId") or ""),
            success=ok,
            amount=Decimal(str(data.get("paidPrice") or "0")),
            provider_ref=token,
        )


class PaytrProvider:
    name = "paytr"

    def __init__(
        self, merchant_id: str, merchant_key: str, merchant_salt: str, test_mode: int = 1,
        client: httpx.Client | None = None,
    ) -> None:
        if not (merchant_id and merchant_key and merchant_salt):
            raise ValueError("paytr: PAYTR_MERCHANT_ID / KEY / SALT zorunlu")
        self._id, self._key, self._salt = merchant_id, merchant_key.encode(), merchant_salt
        self._test_mode = int(test_mode)
        self._client = client or httpx.Client(timeout=10.0)

    def __repr__(self) -> str:
        return f"PaytrProvider(merchant_id={self._id!r}, test_mode={self._test_mode}, keys='***')"

    def _sign(self, text: str) -> str:
        return base64.b64encode(hmac.new(self._key, text.encode(), hashlib.sha256).digest()).decode()

    def start(self, req: CheckoutRequest) -> CheckoutStart:
        amount = str(to_kurus(req.amount))
        basket = base64.b64encode(json.dumps([[req.description, tl(req.amount), 1]]).encode()).decode()
        no_installment, max_installment, currency = "1", "0", "TL"
        # Doküman sırası: merchant_id + user_ip + merchant_oid + email + payment_amount + user_basket
        #                 + no_installment + max_installment + currency + test_mode, sonuna salt
        hash_str = (
            f"{self._id}{req.buyer_ip}{req.merchant_oid}{req.buyer_email}{amount}{basket}"
            f"{no_installment}{max_installment}{currency}{self._test_mode}"
        )
        form = {
            "merchant_id": self._id, "user_ip": req.buyer_ip, "merchant_oid": req.merchant_oid,
            "email": req.buyer_email, "payment_amount": amount, "paytr_token": self._sign(hash_str + self._salt),
            "user_basket": basket, "debug_on": "0", "no_installment": no_installment,
            "max_installment": max_installment, "user_name": req.buyer_name, "user_address": "Türkiye",
            "user_phone": "05000000000", "merchant_ok_url": req.ok_url, "merchant_fail_url": req.fail_url,
            "timeout_limit": "30", "currency": currency, "test_mode": str(self._test_mode), "lang": "tr",
        }
        r = self._client.post(PAYTR_TOKEN_URL, data=form)
        data = r.json() if r.is_success else {}
        if data.get("status") != "success":
            raise ProviderError(f"PayTR token alınamadı: status={r.status_code}")
        return CheckoutStart(iframe_url=f"https://www.paytr.com/odeme/guvenli/{data['token']}")

    def verify_notification(self, form: dict[str, str]) -> PaymentResult:
        oid = form.get("merchant_oid", "")
        status = form.get("status", "")
        total = form.get("total_amount", "")  # kuruş, imza ham metinle hesaplanır
        expected = self._sign(f"{oid}{self._salt}{status}{total}")
        if not safe_equals(expected, form.get("hash", "")):
            raise InvalidSignature
        try:
            amount = Decimal(total) / 100
        except ArithmeticError:
            raise InvalidSignature from None
        return PaymentResult(merchant_oid=oid, success=status == "success", amount=amount)


def check_live_lock(settings: Settings) -> None:
    """PAYMENT_LIVE=false iken canlı adres/mod → uygulama açılmaz (KARARLAR.md: gerçek para yok)."""
    if settings.payment_live:
        return
    p = settings.payment_provider.lower()
    if p == "iyzico" and settings.iyzico_base_url.rstrip("/") != IYZICO_SANDBOX:
        raise RuntimeError("PAYMENT_LIVE=false iken iyzico yalnızca sandbox adresiyle çalışır")
    if p == "paytr" and int(settings.paytr_test_mode) != 1:
        raise RuntimeError("PAYMENT_LIVE=false iken PAYTR_TEST_MODE=1 olmalı")


def build_provider(settings: Settings) -> PaymentProvider:
    check_live_lock(settings)
    p = settings.payment_provider.lower()
    if p == "fake":
        if settings.is_prod and settings.payment_live:
            raise RuntimeError("Canlı ortamda fake ödeme kullanılamaz")
        return FakeProvider()
    if p == "iyzico":
        return IyzicoProvider(settings.iyzico_api_key, settings.iyzico_secret_key, settings.iyzico_base_url)
    if p == "paytr":
        return PaytrProvider(
            settings.paytr_merchant_id, settings.paytr_merchant_key, settings.paytr_merchant_salt,
            settings.paytr_test_mode,
        )
    raise ValueError(f"Bilinmeyen PAYMENT_PROVIDER: {p!r}")
