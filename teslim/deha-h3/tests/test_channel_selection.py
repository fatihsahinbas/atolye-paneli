def test_phone_exists_uses_sms(client, db, make_order, customer_phone, headers):
    order = make_order(customer_phone)
    r = client.post(f"/orders/{order.id}/status?new_status=READY", headers=headers)
    assert r.status_code == 200
    assert r.json()["channel"] == "SMS"
    assert r.json()["notification"] == "SENT"


def test_email_fallback(client, db, make_order, customer_email, headers):
    order = make_order(customer_email)
    r = client.post(f"/orders/{order.id}/status?new_status=READY", headers=headers)
    assert r.status_code == 200
    assert r.json()["channel"] == "EMAIL"
    assert r.json()["notification"] == "SENT"


def test_no_phone_no_email_skipped(client, db, make_order, customer_none, headers):
    order = make_order(customer_none)
    r = client.post(f"/orders/{order.id}/status?new_status=READY", headers=headers)
    assert r.status_code == 200
    assert r.json()["channel"] == "SKIPPED"
    assert r.json()["notification"] == "SKIPPED"


def test_smtp_failure_marks_failed_but_order_updates(
    client, db, make_order, customer_email, headers
):
    from tests.conftest import FakeSMTP
    FakeSMTP.fail = True
    order = make_order(customer_email)
    r = client.post(f"/orders/{order.id}/status?new_status=READY", headers=headers)
    assert r.status_code == 200
    assert r.json()["notification"] == "FAILED"
    assert r.json()["status"] == "READY"