"""User directory (for auth) and the account repository (RBAC-scoped)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Principal, Role
from app.models.organization import Account, User
from app.repositories.base import ScopedRepository


class UserDirectory:
    """Plain, unscoped user lookups used *before* a principal exists (login).

    This is the only repository that is not principal-scoped, by necessity — it
    is how a principal is constructed in the first place.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower().strip()))

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def list_users(self) -> list[User]:
        return list(self.session.scalars(select(User).order_by(User.id)))

    def build_principal(self, user: User) -> Principal:
        """Materialise the immutable :class:`Principal` for an authenticated user."""
        role = Role(user.role)
        assigned = frozenset(a.id for a in user.assigned_accounts) if role == Role.SUPPORT else frozenset()
        return Principal(
            user_id=user.id,
            email=user.email,
            name=user.name,
            role=role,
            account_id=user.account_id,
            assigned_account_ids=assigned,
        )


class AccountRepository(ScopedRepository):
    """Account reads, always scoped to what the principal may see."""

    def get_by_id(self, account_id: int) -> Account | None:
        stmt = self.apply_account_scope(select(Account).where(Account.id == account_id), Account.id)
        return self.session.scalar(stmt)

    def get_by_code(self, code: str) -> Account | None:
        stmt = self.apply_account_scope(
            select(Account).where(Account.code == code.strip().upper()), Account.id
        )
        return self.session.scalar(stmt)

    def list_accounts(self) -> list[Account]:
        stmt = self.apply_account_scope(select(Account).order_by(Account.code), Account.id)
        return list(self.session.scalars(stmt))
