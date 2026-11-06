"""Şifre hash (Argon2id, #11), oturum token'ı, CSRF, HMAC yardımcıları."""
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_ph = PasswordHasher()  # Argon2id, güvenli varsayılanlar


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


# Zamanlama saldırısında kullanıcı var/yok ayrımı sızmasın diye sahte hash
DUMMY_HASH = _ph.hash("dummy-password-for-timing")


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def token_digest(token: str) -> str:
    """DB'de oturum token'ının kendisi değil SHA-256 özeti saklanır."""
    return hashlib.sha256(token.encode()).hexdigest()


def safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def hmac_sha256(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
