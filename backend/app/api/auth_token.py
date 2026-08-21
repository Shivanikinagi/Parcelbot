"""Signed session tokens for mock auth.

Mock auth means we don't verify passwords — the user picks an identity. But the
token is genuinely signed (HMAC-SHA256 over the email with the app secret), so a
client cannot forge or tamper with an identity, and RBAC downstream is real.
Swapping this for OAuth/OIDC later only changes how the email is established;
every layer below is unaffected.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from app.core.config import settings


def _sign(payload: str) -> str:
    digest = hmac.new(settings.auth_secret.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def make_token(email: str) -> str:
    email = email.lower().strip()
    body = f"{email}|{_sign(email)}"
    return base64.urlsafe_b64encode(body.encode()).decode().rstrip("=")


def parse_token(token: str) -> str | None:
    """Return the verified email, or None if the token is invalid/tampered."""
    try:
        padded = token + "=" * (-len(token) % 4)
        body = base64.urlsafe_b64decode(padded.encode()).decode()
        email, sig = body.rsplit("|", 1)
    except Exception:
        return None
    return email if hmac.compare_digest(sig, _sign(email)) else None
