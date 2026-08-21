"""Role model and the :class:`Principal` — the authenticated caller identity.

The Principal is threaded from the API layer down into every repository call.
**Access control is enforced by the repository layer using this object**, never
by prompt text. The agent and tools receive a Principal and cannot widen their
own scope: a customer Principal simply cannot express a query that returns
another customer's rows, because the repository adds the ownership filter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    """RBAC roles, ordered loosely from least to most privileged."""

    CUSTOMER = "customer"
    SUPPORT = "support"
    MANAGER = "manager"
    ADMIN = "admin"

    @property
    def is_internal(self) -> bool:
        """Internal staff can see cross-account context; customers cannot."""
        return self in {Role.SUPPORT, Role.MANAGER, Role.ADMIN}

    @property
    def is_privileged(self) -> bool:
        """Managers/admins can see everything across all accounts."""
        return self in {Role.MANAGER, Role.ADMIN}


# Coarse-grained capability flags. Fine-grained *data* scoping happens in the
# repositories; this table gates whole categories of action (defense in depth).
_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.CUSTOMER: frozenset(
        {"chat", "read_own", "create_ticket", "request_escalation"}
    ),
    Role.SUPPORT: frozenset(
        {
            "chat",
            "read_own",
            "read_assigned",
            "create_ticket",
            "update_ticket",
            "create_escalation",
            "create_task",
            "view_ops",
        }
    ),
    Role.MANAGER: frozenset(
        {
            "chat",
            "read_own",
            "read_assigned",
            "read_all",
            "create_ticket",
            "update_ticket",
            "create_escalation",
            "create_task",
            "view_ops",
            "view_analytics",
            "view_audit",
        }
    ),
    Role.ADMIN: frozenset(
        {
            "chat",
            "read_own",
            "read_assigned",
            "read_all",
            "create_ticket",
            "update_ticket",
            "create_escalation",
            "create_task",
            "view_ops",
            "view_analytics",
            "view_audit",
            "manage_users",
            "manage_settings",
        }
    ),
}


@dataclass(frozen=True)
class Principal:
    """Immutable authenticated identity passed through every layer."""

    user_id: int
    email: str
    name: str
    role: Role
    #: For customers: the single account they belong to.
    account_id: int | None = None
    #: For support agents: the set of accounts assigned to them.
    assigned_account_ids: frozenset[int] = field(default_factory=frozenset)

    # --- capability checks ----------------------------------------------
    def can(self, permission: str) -> bool:
        return permission in _PERMISSIONS.get(self.role, frozenset())

    def require(self, permission: str) -> None:
        from app.core.exceptions import AccessDeniedError

        if not self.can(permission):
            raise AccessDeniedError(
                "You do not have permission to perform this action.",
                details={"required_permission": permission, "role": self.role.value},
            )

    # --- data-scope helpers used by repositories ------------------------
    def accessible_account_ids(self) -> set[int] | None:
        """Return the account ids this principal may read.

        ``None`` means "unrestricted" (managers/admins). An empty set means
        "nothing", which repositories translate into a query that returns no
        rows — safe by default.
        """
        if self.role.is_privileged:
            return None
        ids: set[int] = set(self.assigned_account_ids)
        if self.account_id is not None:
            ids.add(self.account_id)
        return ids

    def can_access_account(self, account_id: int) -> bool:
        allowed = self.accessible_account_ids()
        return allowed is None or account_id in allowed
