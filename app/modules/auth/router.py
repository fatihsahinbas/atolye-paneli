from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import get_db
from app.core.deps import SESSION_COOKIE, csrf_protect, current_user, load_session
from app.core.templating import render
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginIn, RegisterIn, first_error
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
