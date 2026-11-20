from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import get_db
from app.core.deps import SESSION_COOKIE, csrf_protect, current_user, load_session
from app.core.security import new_token, safe_equals
from app.core.templating import render
from app.modules.auth.models import User
from app.modules.auth.password_reset import complete_reset, request_reset, valid_reset
from app.modules.auth.reset_email import send_reset_email
from app.modules.auth.schemas import LoginIn, RegisterIn, _email, first_error
from app.modules.auth.service import (
    AuthError,
    authenticate,
    create_session,
    delete_account,
    destroy_session,
    register_workshop,
)

router = APIRouter(tags=["auth"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _login_response(request: Request, db: Session, user: User) -> Response:
    s = _settings(request)
    token = create_session(db, user, s.session_ttl_hours)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=s.session_ttl_hours * 3600,
        httponly=True,  # JS okuyamaz
        secure=s.cookie_secure,  # yalnızca HTTPS
        samesite="lax",
    )
    return resp


@router.get("/kayit")
def register_form(request: Request):
    return render(request, "auth/register.html")


@router.post("/kayit")
def register(
    request: Request,
    db: Session = Depends(get_db),
    workshop_name: str = Form(""),
    slug: str = Form(""),
    full_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
):
    if not request.app.state.register_limiter.hit(f"reg:{_client_ip(request)}"):
        return render(request, "auth/register.html", {"error": "Çok fazla deneme. Biraz sonra tekrar deneyin."}, 429)
    form = {"workshop_name": workshop_name, "slug": slug, "full_name": full_name, "email": email}
    try:
        data = RegisterIn(**form, password=password)
        user = register_workshop(db, data)
    except ValidationError as e:
        return render(request, "auth/register.html", {"error": first_error(e), "form": form}, 422)
    except AuthError as e:
        return render(request, "auth/register.html", {"error": str(e), "form": form}, 400)
    return _login_response(request, db, user)


@router.get("/giris")
def login_form(request: Request, db: Session = Depends(get_db)):
    if load_session(request, db):
        return RedirectResponse("/", status_code=303)
    return render(request, "auth/login.html")


@router.post("/giris")
def login(request: Request, db: Session = Depends(get_db), email: str = Form(""), password: str = Form("")):
    limiter = request.app.state.login_limiter
    ip_ok = limiter.hit(f"ip:{_client_ip(request)}")
    acct_ok = limiter.hit(f"acct:{email.strip().lower()}")
    if not (ip_ok and acct_ok):
        return render(request, "auth/login.html", {"error": "Çok fazla deneme. 15 dakika sonra tekrar deneyin."}, 429)
    try:
        user = authenticate(db, LoginIn(email=email, password=password))
    except (ValidationError, AuthError):
        return render(request, "auth/login.html", {"error": "E-posta veya şifre hatalı", "email": email}, 401)
    return _login_response(request, db, user)


@router.post("/cikis", dependencies=[Depends(csrf_protect)])
def logout(request: Request, db: Session = Depends(get_db)):
    destroy_session(db, request.cookies.get(SESSION_COOKIE))
    resp = RedirectResponse("/giris", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@router.get("/hesap")
def account(request: Request, user: User = Depends(current_user)):
    return render(request, "auth/account.html")


@router.post("/hesap/sil", dependencies=[Depends(csrf_protect)])
def account_delete(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    password: str = Form(""),
):
    try:
        delete_account(db, user, password, _settings(request).media_root)
    except AuthError as e:
        return render(request, "auth/account.html", {"error": str(e)}, 400)
    resp = RedirectResponse("/giris", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


RESET_CSRF_COOKIE = "atolye_reset_csrf"


def _reset_form(request: Request, template: str, context: dict | None = None, status: int = 200):
    csrf = new_token(24)
    resp = render(request, template, {**(context or {}), "reset_csrf": csrf}, status)
    resp.set_cookie(RESET_CSRF_COOKIE, csrf, max_age=1800, httponly=True,
                    secure=_settings(request).cookie_secure, samesite="strict")
    return resp


def _check_reset_csrf(request: Request, value: str):
    stored = request.cookies.get(RESET_CSRF_COOKIE, "")
    if not stored or not value or not safe_equals(stored, value):
        raise HTTPException(status_code=403)


@router.get("/sifremi-unuttum")
def forgot_form(request: Request):
    return _reset_form(request, "auth/forgot_password.html")


@router.post("/sifremi-unuttum")
def forgot_password(request: Request, db: Session = Depends(get_db),
                    email: str = Form(""), reset_csrf: str = Form("")):
    _check_reset_csrf(request, reset_csrf)
    limiter = request.app.state.reset_limiter
    allowed_ip = limiter.hit(f"ip:{_client_ip(request)}")
    allowed_email = limiter.hit(f"email:{email.strip().lower()}")
    if not (allowed_ip and allowed_email):
        return _reset_form(request, "auth/forgot_password.html", {"error": "Çok fazla istek. Daha sonra deneyin."}, 429)
    try:
        normalized = _email(email)
    except ValueError:
        return _reset_form(request, "auth/forgot_password.html", {"error": "Geçerli bir e-posta girin."}, 422)

    def sender(address, link):
        if _settings(request).env == "test":
            request.app.state.reset_mail_outbox.append((address, link))
        else:
            send_reset_email(_settings(request), address, link)

    try:
        request_reset(db, normalized, str(request.base_url), sender)
    except Exception:
        # Sunucu hatası/kullanıcı varlığı ayrımını istemciye sızdırma.
        import logging
        logging.getLogger("atolye.auth").exception("Şifre sıfırlama e-postası gönderilemedi")
    msg = "Bu e-posta kayıtlıysa sıfırlama bağlantısı gönderildi."
    return render(request, "auth/forgot_password.html", {"success": msg})


@router.get("/sifre-yenile")
def reset_form(request: Request, token: str = "", db: Session = Depends(get_db)):
    if valid_reset(db, token) is None:
        return render(request, "auth/reset_password.html", {"invalid": True}, 400)
    return _reset_form(request, "auth/reset_password.html", {"token": token})


@router.post("/sifre-yenile")
def reset_password(request: Request, db: Session = Depends(get_db),
                   token: str = Form(""), password: str = Form(""),
                   password_confirm: str = Form(""), reset_csrf: str = Form("")):
    _check_reset_csrf(request, reset_csrf)
    if not (10 <= len(password) <= 128) or password != password_confirm:
        return _reset_form(request, "auth/reset_password.html", {
            "token": token, "error": "Şifreler aynı olmalı ve 10–128 karakter içermeli."
        }, 422)
    if not complete_reset(db, token, password):
        return render(request, "auth/reset_password.html", {"invalid": True}, 400)
    resp = RedirectResponse("/giris?reset=ok", status_code=303)
    resp.delete_cookie(RESET_CSRF_COOKIE)
    resp.delete_cookie(SESSION_COOKIE)
    return resp
