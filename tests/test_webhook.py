import json
import time

from app.core.security import hmac_sha256
from tests.conftest import make_client

SECRET = "whsec_test_123"


def _post(client, payload: dict, ts: int | None = None, secret: str = SECRET):
    body = json.dumps(payload).encode()
    ts = ts or int(time.time())
    sig = hmac_sha256(secret, f"{ts}.".encode() + body)
    return client.post("/webhooks/odeme", content=body,
                       headers={"X-Timestamp": str(ts), "X-Signature": sig, "Content-Type": "application/json"})


def test_valid_and_duplicate(app):
    c = make_client(app)
    assert _post(c, {"event_id": "evt_1"}).json() == {"status": "ok"}
    assert _post(c, {"event_id": "evt_1"}).json() == {"status": "duplicate"}


def test_bad_signature(app):
    assert _post(make_client(app), {"event_id": "evt_2"}, secret="yanlis").status_code == 401


def test_replay_old_timestamp(app):
    assert _post(make_client(app), {"event_id": "evt_3"}, ts=int(time.time()) - 3600).status_code == 401
