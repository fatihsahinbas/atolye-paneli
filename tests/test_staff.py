from sqlalchemy import select

from app.modules.auth.models import User
from tests.conftest import csrf, make_client, register


def test_staff_owner_tenant_security(app):
    a = make_client(app)
    b = make_client(app)
    register(a, "atolye-a", "owner-a@example.com")
    register(b, "atolye-b", "owner-b@example.com")
    token = csrf(a, "/personel")
    staff = {"full_name": "Usta Bir", "email": "usta@example.com", "password": "guclu-sifre-123"}
    create = a.post("/personel", data={"csrf_token": token, **staff})
    assert create.status_code == 303
    assert "Usta Bir" in a.get("/personel").text
    assert "Usta Bir" not in b.get("/personel").text
    with app.state.SessionLocal() as db:
        staff_id = db.scalar(select(User).where(User.email == "usta@example.com")).id
    assert b.post(f"/personel/{staff_id}/durum", data={"csrf_token": csrf(b, "/personel")}).status_code == 404
    assert a.post(f"/personel/{staff_id}/durum", data={"csrf_token": "yanlis"}).status_code == 403
    assert a.post(f"/personel/{staff_id}/durum", data={"csrf_token": token}).status_code == 303
    with app.state.SessionLocal() as db:
        assert not db.get(User, staff_id).is_active
    assert a.post(f"/personel/{staff_id}/durum", data={"csrf_token": token}).status_code == 303
    duplicate = {**staff, "full_name": "Baska"}
    assert a.post("/personel", data={"csrf_token": token, **duplicate}).status_code == 409
    staff_client = make_client(app)
    staff_login = staff_client.post("/giris", data={"email": "usta@example.com", "password": "guclu-sifre-123"})
    assert staff_login.status_code == 303
    assert staff_client.get("/personel").status_code == 403
    other = {**staff, "full_name": "Yetkisiz", "email": "n@example.com"}
    assert staff_client.post("/personel", data={"csrf_token": csrf(staff_client), **other}).status_code == 403
