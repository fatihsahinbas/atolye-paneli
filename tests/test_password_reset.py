"""H3: e-posta ile süreli, tek kullanımlık şifre sıfırlama."""
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import select

from app.core.db import utcnow
from app.modules.auth.models import PasswordResetToken
from tests.conftest import make_client, register


def _request(client, email):
    import re
    form = client.get('/sifremi-unuttum')
    csrf = re.search(r'name="reset_csrf" value="([^"]+)"', form.text).group(1)
    return client.post('/sifremi-unuttum', data={'email':email, 'reset_csrf':csrf})


def _reset(client, url, pwd):
    import re
    form = client.get(url)
    csrf = re.search(r'name="reset_csrf" value="([^"]+)"', form.text).group(1)
    token = parse_qs(urlsplit(url).query)['token'][0]
    return client.post('/sifre-yenile', data={
        'reset_csrf':csrf, 'token': token, 'password': pwd, 'password_confirm':pwd
    })


def test_reset_success_single_use_and_old_password_denied(app):
    client = make_client(app)
    register(client, 'atolye-a', 'user@example.com')
    assert _request(client, 'user@example.com').status_code == 200
    address, link = app.state.reset_mail_outbox[-1]
    assert address == 'user@example.com'
    assert _reset(client, link, 'yeni-guclu-sifre-2').status_code == 303
    assert client.get(link).status_code == 400
    assert client.post('/giris', data={'email':address, 'password':'cok-gizli-sifre-1'}).status_code == 401
    assert client.post('/giris', data={'email':address, 'password':'yeni-guclu-sifre-2'}).status_code == 303


def test_nonexistent_email_generic_and_expiry(app):
    client = make_client(app)
    register(client, 'atolye-b', 'known@example.com')
    assert _request(client, 'unknown@example.com').status_code == 200
    assert not app.state.reset_mail_outbox
    assert _request(client, 'known@example.com').status_code == 200
    link = app.state.reset_mail_outbox[-1][1]
    with app.state.SessionLocal() as db:
        reset = db.scalar(select(PasswordResetToken))
        reset.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get(link).status_code == 400


def test_reset_missing_csrf_and_replaced_token(app):
    client = make_client(app)
    register(client, 'atolye-c', 'known@example.com')
    assert client.post('/sifremi-unuttum', data={'email':'known@example.com'}).status_code == 403
    _request(client, 'known@example.com')
    old_link = app.state.reset_mail_outbox[-1][1]
    _request(client, 'known@example.com')
    assert client.get(old_link).status_code == 400
