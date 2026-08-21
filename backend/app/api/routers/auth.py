"""Auth router: mock login (identity selection), current user, demo directory."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth_token import make_token
from app.api.deps import get_db, get_principal
from app.core.exceptions import AuthenticationError
from app.core.security import Principal
from app.repositories.organization_repo import UserDirectory
from app.schemas.api import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user, account_map: dict[int, str]) -> UserOut:
    return UserOut(
        id=user.id, name=user.name, email=user.email, role=user.role,
        account_code=(user.account.code if user.account else None),
        account_name=(user.account.name if user.account else None),
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = UserDirectory(db).get_by_email(body.email)
    if user is None or not user.is_active:
        raise AuthenticationError("Unknown user. Pick one of the seeded demo identities.")
    return LoginResponse(token=make_token(user.email), user=_user_out(user, {}))


@router.get("/me", response_model=UserOut)
def me(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> UserOut:
    user = UserDirectory(db).get_by_id(principal.user_id)
    return _user_out(user, {})


@router.get("/users", response_model=list[UserOut])
def demo_users(db: Session = Depends(get_db)) -> list[UserOut]:
    """List seeded identities for the login screen (demo convenience)."""
    users = UserDirectory(db).list_users()
    return [_user_out(u, {}) for u in users]
