import hashlib
import hmac
import secrets
from dataclasses import dataclass

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    csrf_token: str


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def new_token_pair() -> TokenPair:
    return TokenPair(
        access_token=secrets.token_urlsafe(32),
        refresh_token=secrets.token_urlsafe(48),
        csrf_token=secrets.token_urlsafe(24),
    )


def hash_token(token: str, secret: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def hash_optional_metadata(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode()).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode(), right.encode())
