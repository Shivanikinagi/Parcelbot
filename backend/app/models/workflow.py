"""State-changing workflow artifacts: escalations and follow-up tasks.

These rows are created only through the confirmed-action flow (agent proposes →
user confirms → executor writes → audit log). Every row records who created it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Escalation(Base, TimestampMixin):
    """An escalation raised for a ticket/account (e.g. breached P1 SLA)."""

    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), nullable=False, index=True)  # ESC-0001
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False, default="P2")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assigned_to: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class FollowUpTask(Base, TimestampMixin):
    """A follow-up action item created off the back of a conversation."""

    __tablename__ = "follow_up_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), nullable=False, index=True)  # TASK-0001
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
