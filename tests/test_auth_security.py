from tests.conftest import csrf, make_client, register


def test_register_sets_secure_cookie(app):
    c = make_client(app)
    r = c.post("/kayit", data={"workshop_name": "Işıl Kuyumculuk", "slug": "isil", "full_name": "Işıl",
                               "email": "isil@ornek.com", "password": "cok-gizli-sifre-1"})
    assert r.status_code == 303
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_register_rejects_weak_password_and_bad_slug(app):
    c = make_client(app)
    r = c.post("/kayit", data={"workshop_name": "X Y", "slug": "Bad Slug!", "full_name": "A B",
                               "email": "a@b.com", "password": "kisa"})
    assert r.status_code == 422


def test_login_generic_error_and_rate_limit(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    c.cookies.clear()
    for _ in range(5):
        r = c.post("/giris", data={"email": "a@ornek.com", "password": "yanlis-sifre"})
        assert r.status_code == 401
        assert "E-posta veya şifre hatalı" in r.text
    r = c.post("/giris", data={"email": "a@ornek.com", "password": "cok-gizli-sifre-1"})
    assert r.status_code == 429  # doğru şifre bile limit dolunca reddedilir


def test_protected_pages_redirect_to_login(app):
    c = make_client(app)
    r = c.get("/")
    assert r.status_code == 303 and r.headers["location"] == "/giris"


def test_csrf_required(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    r = c.post("/musteriler", data={"full_name": "Kimse"})
    assert r.status_code == 403
    r = c.post("/musteriler", data={"full_name": "Kimse", "csrf_token": "sahte"})
    assert r.status_code == 403


def test_logout_revokes_session(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    token = c.cookies.get("atolye_session")
    c.post("/cikis", data={"csrf_token": csrf(c)})
    c2 = make_client(app)
    c2.cookies.set("atolye_session", token)
    assert c2.get("/").status_code == 303  # çalınan eski token işe yaramaz


def test_security_headers(app):
    r = make_client(app).get("/giris")
    h = r.headers
    assert "default-src 'self'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "access-control-allow-origin" not in h


def test_untrusted_host_rejected(app):
    c = make_client(app)
    assert c.get("/giris", headers={"host": "evil.example"}).status_code == 400


def test_staff_cannot_do_owner_actions(app, settings):
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.modules.auth.models import Role, User

    owner = make_client(app)
    register(owner, "atolye-a", "a@ornek.com")
    with app.state.SessionLocal() as db:
        ws_id = db.scalar(select(User.workshop_id).where(User.email == "a@ornek.com"))
        db.add(User(workshop_id=ws_id, email="usta@ornek.com", full_name="Usta",
                    password_hash=hash_password("usta-sifresi-123"), role=Role.STAFF))
        db.commit()
    staff = make_client(app)
    staff.post("/giris", data={"email": "usta@ornek.com", "password": "usta-sifresi-123"})
    t = csrf(staff)
    r = staff.post("/urunler", data={"csrf_token": t, "name": "X", "pricing_type": "FIXED", "base_price": "1"})
    assert r.status_code == 403


def test_owner_account_delete_removes_everything(app):
    c = make_client(app)
    register(c, "atolye-a", "a@ornek.com")
    r = c.post("/hesap/sil", data={"csrf_token": csrf(c), "password": "cok-gizli-sifre-1"})
    assert r.status_code == 303
    assert make_client(app).get("/v/atolye-a").status_code == 404
    r = make_client(app).post("/giris", data={"email": "a@ornek.com", "password": "cok-gizli-sifre-1"})
    assert r.status_code == 401
