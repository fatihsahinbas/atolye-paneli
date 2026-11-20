from app.models.notification import Notification
from tests.conftest import FakeSMTP


def _make_failed(db, order):
    n = Notification(order_id=order.id, channel="EMAIL", status="FAILED")
    db.add(n); db.commit(); db.refresh(n)
    return n


def test_retry_failed_becomes_sent(client, db, make_order, customer_email, headers):
    order = make_order(customer_email)
    n = _make_failed(db, order)

    r = client.post(f"/bildirimler/{n.id}/tekrar", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "SENT"

    db.refresh(n)
    assert n.status == "SENT"


def test_retry_sent_is_idempotent(client, db, make_order, customer_email, headers):
    order = make_order(customer_email)
    n = Notification(order_id=order.id, channel="EMAIL", status="SENT")
    db.add(n); db.commit(); db.refresh(n)

    FakeSMTP.instances.clear()
    r = client.post(f"/bildirimler/{n.id}/tekrar", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "SENT"
    # hiç gönderim olmadı
    assert len(FakeSMTP.instances) == 0


def test_other_workshop_notification_404(
    client, db, other_workshop, customer_email, make_order, headers
):
    from app.models.order import Order
    foreign_order = Order(workshop_id=other_workshop.id, customer_id=customer_email.id, status="NEW")
    db.add(foreign_order); db.commit(); db.refresh(foreign_order)
    n = Notification(order_id=foreign_order.id, channel="EMAIL", status="FAILED")
    db.add(n); db.commit(); db.refresh(n)

    r = client.post(f"/bildirimler/{n.id}/tekrar", headers=headers)
    assert r.status_code == 404


def test_missing_csrf_403(client, db, make_order, customer_email, workshop):
    order = make_order(customer_email)
    n = _make_failed(db, order)
    r = client.post(
        f"/bildirimler/{n.id}/tekrar",
        headers={"X-Workshop-Id": str(workshop.id)},  # CSRF yok
    )
    assert r.status_code == 403