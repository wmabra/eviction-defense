"""Authentication utilities — password hashing and stateless signed tokens.

Uses only the Python standard library (no extra dependencies):

* Passwords are hashed with PBKDF2-HMAC-SHA256 (salt + iterations stored inline).
* Session tokens are HMAC-SHA256-signed, base64url-encoded, stateless JSON blobs
  carrying the user id and an expiry. The signing key is ``settings.secret_key``.
"""
import base64
import hashlib
import hmac
import json
import secrets
import string
import time
from typing import Optional

from app.config import settings

PBKDF2_ITERATIONS = 200_000
TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days

_PASSWORD_ALPHABET = string.ascii_letters + string.digits


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a fresh random salt."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison of a password against a stored hash."""
    try:
        _algo, iterations, salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


def generate_temp_password(length: int = 12) -> str:
    """Generate a readable temporary password (letters + digits, no symbols)."""
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


# --------------------------------------------------------------------------- #
# Signed tokens
# --------------------------------------------------------------------------- #
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_token(user_id: str, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    """Create a signed, expiring token for a user."""
    payload = {"uid": user_id, "exp": time.time() + ttl_seconds}
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _b64url_encode(_sign(body))
    return f"{body}.{signature}"


def verify_token(token: str) -> Optional[str]:
    """Validate a token and return the user id, or None if invalid/expired."""
    try:
        body, signature = token.split(".", 1)
        expected = _b64url_encode(_sign(body))
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_b64url_decode(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("uid")
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _sign(body: str) -> bytes:
    return hmac.new(settings.secret_key.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
