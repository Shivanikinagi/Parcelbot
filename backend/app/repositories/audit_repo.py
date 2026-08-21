"""Audit log and tool-execution telemetry writers/readers."""

from __future__ import annotations

from sqlalchemy import select

from app.core.security import Principal
from app.models.audit import AuditLog, ToolExecution
from app.repositories.base import ScopedRepository


class AuditRepository(ScopedRepository):
    """Writes the immutable audit trail and reads it back for managers/admins."""

    def record(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        account_id: int | None = None,
        success: bool = True,
        details: dict | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            request_id=request_id,
            actor_user_id=self.principal.user_id,
            actor_role=self.principal.role.value,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            account_id=account_id,
            success=success,
            details=details or {},
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_recent(self, limit: int = 100) -> list[AuditLog]:
        self.principal.require("view_audit")
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))


class ToolExecutionRepository(ScopedRepository):
    def record(
        self,
        *,
        tool_name: str,
        arguments: dict,
        result_summary: str,
        success: bool,
        latency_ms: int,
        conversation_id: int | None = None,
        message_id: int | None = None,
        request_id: str | None = None,
        error: str | None = None,
    ) -> ToolExecution:
        row = ToolExecution(
            request_id=request_id,
            conversation_id=conversation_id,
            message_id=message_id,
            tool_name=tool_name,
            arguments=arguments,
            result_summary=result_summary[:2000],
            success=success,
            latency_ms=latency_ms,
            error=error,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_recent(self, limit: int = 200) -> list[ToolExecution]:
        stmt = select(ToolExecution).order_by(ToolExecution.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))
