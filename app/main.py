"""Uygulama fabrikası: middleware, hata yakalama, router kayıtları."""
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import Settings, get_settings
from app.core.db import Base, build_engine, build_sessionmaker
from app.core.deps import LoginRequired
from app.core.logging import setup_logging
from app.core.ratelimit import RateLimiter
from app.core.templating import render
from app.modules.auth.router import router as auth_router
from app.modules.auth.staff import router as staff_router
from app.modules.catalog.router import router as catalog_router
from app.modules.customers.router import router as customers_router
from app.modules.notifications.service import Notifier, build_notifier
from app.modules.orders.router import router as orders_router
from app.modules.payments.router import router as payments_router
from app.modules.showcase.router import router as showcase_router
from app.modules.tracking.router import router as tracking_router

log = logging.getLogger("atolye")

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


def create_app(settings: Settings | None = None, notifier: Notifier | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        # Production'da otomatik API dokümanı kapalı
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
    )

    engine = build_engine(settings.database_url)
    if not settings.is_prod:
        from app import models  # noqa: F401  tüm tabloları kaydet

        Base.metadata.create_all(engine)  # prod'da yalnızca Alembic
    app.state.settings = settings
    app.state.engine = engine
    app.state.SessionLocal = build_sessionmaker(engine)
    app.state.login_limiter = RateLimiter(settings.login_rate_limit, settings.login_rate_window_sec)
    app.state.register_limiter = RateLimiter(10, 3600)
    app.state.reset_limiter = RateLimiter(5, 3600)
    app.state.reset_mail_outbox = []  # only for automated tests
    # Somut sınıf burada seçilmez; kanal .env'deki NOTIFY_CHANNEL'dan gelir.
    app.state.notifier = notifier or build_notifier(settings)
    Path(settings.media_root).mkdir(parents=True, exist_ok=True)

    # --- Middleware -------------------------------------------------------
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    # CORS middleware bilinçli olarak YOK: uygulama tek origin, cross-origin istek kabul edilmez (#8)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # Checklist #9
        response = await call_next(request)
        h = response.headers
        h["Content-Security-Policy"] = CSP
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "same-origin"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.is_prod:
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"  # #10
        return response

    # --- Hata yakalama: kullanıcıya genel mesaj, detay sadece log'a (#13) ---
    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc: LoginRequired):
        if request.headers.get("HX-Request"):
            from fastapi.responses import Response

            return Response(status_code=401, headers={"HX-Redirect": "/giris"})
        return RedirectResponse("/giris", status_code=303)

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException):
        messages = {403: "Bu işlem için yetkiniz yok.", 404: "Aradığınız sayfa bulunamadı.", 429: "Çok fazla istek."}
        msg = messages.get(exc.status_code, "İstek işlenemedi.")
        return render(request, "errors/message.html", {"message": msg}, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        return render(request, "errors/message.html", {"message": "Gönderilen bilgiler geçersiz."}, 422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("Beklenmeyen hata: %s %s", request.method, request.url.path)
        return render(request, "errors/message.html", {"message": "Bir hata oluştu. Lütfen tekrar deneyin."}, 500)

    # --- Router'lar ---------------------------------------------------------
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    for r in (auth_router, staff_router, orders_router, customers_router, catalog_router,
              tracking_router, showcase_router, payments_router):
        app.include_router(r)

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"status": "ok"}

    return app
