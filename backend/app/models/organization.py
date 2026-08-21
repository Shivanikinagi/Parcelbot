"""Accounts, users, and the support-agent ↔ account assignment table.

Schema mirrors the assessment workbook's ``accounts`` sheet. Each row keeps a
human-facing business ``code`` (e.g. ``ACCT-001``) alongside an integer surrogate
key used for foreign keys and RBAC scoping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.logistics import Agreement, Order, Ticket

# Many-to-many: which support agents are assigned to which accounts.
# This backs the SUPPORT role's data scope in the repository layer.
agent_account_assignments = Table(
    "agent_account_assignments",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("account_id", ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
)


class Account(Base, TimestampMixin):
    """A ParcelPilot business customer (the unit of data isolation)."""

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("code", name="uq_accounts_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Business identifier from the dataset, e.g. "ACCT-001".
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    #: enterprise | growth | standard
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    csm: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    #: Filename of the signed agreement in the source pack, if any.
    contract_file: Mapped[str | None] = mapped_column(String(200))
    premium_support: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #: 0-100 composite health score computed at seed time for the ops dashboard.
    health_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)

    users: Mapped[list["User"]] = relationship(back_populates="account")
    orders: Mapped[list["Order"]] = relationship(back_populates="account")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="account")
    agreements: Mapped[list["Agreement"]] = relationship(back_populates="account")


class User(Base, TimestampMixin):
    """A person who signs in — either a customer contact or internal staff."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    #: One of app.core.security.Role values.
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: For customers: the account they belong to. Null for internal staff.
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    account: Mapped["Account | None"] = relationship(back_populates="users")

    #: For support agents: accounts they are assigned to.
    assigned_accounts: Mapped[list["Account"]] = relationship(
        secondary=agent_account_assignments
    )
