"""FastAPI dependencies: DB session, authenticated principal, rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.api.auth_token import parse_token
from app.core.config import settings
from app.core.exceptions import AuthenticationError, RateLimitedError
from app.core.logging import request_id_ctx
from app.core.security import Principal
from app.db.base import get_session
from app.repositories.organization_repo import UserDirectory
from app.tools.base import ToolContext


def get_db() -> Session:  # thin alias so routers depend on the API layer
    yield from get_session()


def get_principal(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    email = parse_token(token)
    if not email:
        raise AuthenticationError("Invalid or tampered session token.")
    user = UserDirectory(db).get_by_email(email)
    if user is None or not user.is_active:
        raise AuthenticationError("Unknown or inactive user.")
    return UserDirectory(db).build_principal(user)


def get_context(
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ToolContext:
    return ToolContext(db, principal, request_id=request_id_ctx.get())


# --- naive in-memory sliding-window rate limiter ---------------------------
_WINDOW_SECONDS = 60
_hits: dict[str, deque] = defaultdict(deque)


def enforce_rate_limit(principal: Principal = Depends(get_principal)) -> Principal:
    now = time.time()
    bucket = _hits[principal.email]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        raise RateLimitedError("Too many requests; please slow down.")
    bucket.append(now)
    return principal
