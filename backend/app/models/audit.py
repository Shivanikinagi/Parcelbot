"""Audit trail and per-tool execution telemetry.

``AuditLog`` is the tamper-evident record of *who did what* — every
state-changing action writes one. ``ToolExecution`` captures observability for
each tool the agent runs (latency, success, arguments, error) and powers the
tool-usage timeline in the UI and the observability dashboard.
"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Immutable record of a security-relevant or state-changing event."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    resource_id: Mapped[str | None] = mapped_column(String(60))
    account_id: Mapped[int | None] = mapped_column(Integer, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ToolExecution(Base, TimestampMixin):
    """Telemetry for a single tool invocation by the agent."""

    __tablename__ = "tool_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, index=True)
    message_id: Mapped[int | None] = mapped_column(Integer, index=True)
    tool_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    arguments: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
