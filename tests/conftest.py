import re

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.notifications.service import ConsoleNotifier

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        secret_key="x" * 40,
        cookie_secure=False,  # TestClient http üzerinden konuşur
        allowed_hosts=["testserver"],
        media_root=str(tmp_path / "media"),
        max_upload_mb=1,
        payment_webhook_secret="whsec_test_123",
    )


@pytest.fixture
def notifier() -> ConsoleNotifier:
    return ConsoleNotifier()


@pytest.fixture
def app(settings, notifier):
    return create_app(settings, notifier)


def make_client(app) -> TestClient:
    return TestClient(app, follow_redirects=False)


def register(client: TestClient, slug: str, email: str, password: str = "cok-gizli-sifre-1") -> None:
    r = client.post("/kayit", data={
        "workshop_name": f"{slug} atölye", "slug": slug, "full_name": "Ayşe Usta",
        "email": email, "password": password,
    })
    assert r.status_code == 303, r.text


def csrf(client: TestClient, path: str = "/musteriler") -> str:
    m = CSRF_RE.search(client.get(path).text)
    assert m, "csrf token bulunamadı"
    return m.group(1)


def seed_order(client: TestClient, consent: bool = True) -> int:
    """Müşteri + sabit fiyatlı ürün + sipariş oluşturur, sipariş id döner."""
    t = csrf(client)
    client.post("/musteriler", data={"csrf_token": t, "full_name": "Mehmet Yılmaz", "phone": "0532 111 22 33",
                                     **({"consent": "true"} if consent else {})})
    client.post("/urunler", data={"csrf_token": t, "name": "Filografi Tablo", "pricing_type": "FIXED",
                                  "base_price": "1000", "show_in_showcase": "true"})
    page = client.get("/siparisler/yeni").text
    cid = re.search(r'name="customer_id"[^>]*>\s*<option value="(\d+)"', page).group(1)
    pid = re.search(r'id="product">\s*<option value="(\d+)"', page).group(1)
    r = client.post("/siparisler", data={"csrf_token": t, "customer_id": cid, "product_id": pid, "quantity": "2",
                                         "due_date": "", "note": ""})
    assert r.status_code == 303, r.text
    return int(r.headers["location"].rsplit("/", 1)[1])
