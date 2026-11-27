"""H3 PROJE 5 · Sürükle-bırak pano: karar sunucuda."""
from sqlalchemy import select

from app.domain.order_status import OrderStatus
from app.modules.orders.models import Order, OrderEvent
from tests.conftest import csrf, make_client, register, seed_order


def _hdr(c):
    return {"X-CSRF-Token": csrf(c)}


def test_valid_move_changes_status_and_logs_event(app, notifier):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    r = c.post(f"/siparisler/{oid}/tasi", data={"to_status": "DESIGN_APPROVAL"}, headers=_hdr(c))
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "status": "DESIGN_APPROVAL"}
    with app.state.SessionLocal() as db:
        o = db.get(Order, oid)
        assert o.status == OrderStatus.DESIGN_APPROVAL
        evs = db.scalars(select(OrderEvent).where(OrderEvent.order_id == oid)).all()
        assert [e.to_status for e in evs][-1] == OrderStatus.DESIGN_APPROVAL
    assert notifier.sent  # rızalı müşteriye bildirim


def test_invalid_move_returns_409_and_keeps_status(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    r = c.post(f"/siparisler/{oid}/tasi", data={"to_status": "DELIVERED"}, headers=_hdr(c))
    assert r.status_code == 409
    assert r.json()["ok"] is False
    with app.state.SessionLocal() as db:
        assert db.get(Order, oid).status == OrderStatus.RECEIVED


def test_move_without_csrf_is_403(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    assert c.post(f"/siparisler/{oid}/tasi", data={"to_status": "DESIGN_APPROVAL"}).status_code == 403


def test_other_workshop_order_is_404(app):
    a, b = make_client(app), make_client(app)
    register(a, "atolye-a", "a@ornek.com")
    register(b, "atolye-b", "b@ornek.com")
    oid = seed_order(a)
    r = b.post(f"/siparisler/{oid}/tasi", data={"to_status": "DESIGN_APPROVAL"}, headers=_hdr(b))
    assert r.status_code == 404


def test_board_cards_are_draggable(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    oid = seed_order(c)
    html = c.get("/").text
    assert f'data-order-id="{oid}"' in html
    assert 'data-status="RECEIVED"' in html
    assert "/static/js/board.js" in html
