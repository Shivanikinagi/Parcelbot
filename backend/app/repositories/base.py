"""Base repository: session + principal + reusable account-scope enforcement."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.core.security import Principal


class ScopedRepository:
    """Base class carrying the DB session and the calling principal.

    Subclasses MUST route every query through :meth:`apply_account_scope` (or
    check :meth:`can_access`) so the principal's data boundary is always
    enforced. This is defense-in-depth: even if a caller passes an arbitrary
    account id, the added ``WHERE account_id IN (...)`` clause makes
    out-of-scope rows unreturnable.
    """

    def __init__(self, session: Session, principal: Principal) -> None:
        self.session = session
        self.principal = principal

    # --- scope helpers ---------------------------------------------------
    def _scope_ids(self) -> set[int] | None:
        """``None`` = unrestricted (manager/admin); otherwise the allowed set."""
        return self.principal.accessible_account_ids()

    def apply_account_scope(
        self, stmt: Select, account_column: InstrumentedAttribute
    ) -> Select:
        """Add the principal's account filter to a SELECT statement."""
        allowed = self._scope_ids()
        if allowed is None:
            return stmt  # privileged: no restriction
        if not allowed:
            # Nothing accessible → force an empty result (safe default).
            return stmt.where(account_column.in_([-1]))
        return stmt.where(account_column.in_(allowed))

    def can_access_account(self, account_id: int | None) -> bool:
        if account_id is None:
            return True
        return self.principal.can_access_account(account_id)
