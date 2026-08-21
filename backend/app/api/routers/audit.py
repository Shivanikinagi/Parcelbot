"""Audit log + tool-execution telemetry (managers/admins, and ops for tools)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_principal
from app.core.security import Principal
from app.repositories.audit_repo import AuditRepository, ToolExecutionRepository

router = APIRouter(tags=["audit"])


@router.get("/audit")
def audit_log(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    rows = AuditRepository(db, principal).list_recent()  # enforces view_audit
    return [
        {
            "id": r.id, "action": r.action, "actor_role": r.actor_role,
            "resource_type": r.resource_type, "resource_id": r.resource_id,
            "account_id": r.account_id, "success": r.success, "details": r.details,
            "request_id": r.request_id, "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/tools/executions")
def tool_executions(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    principal.require("view_ops")
    rows = ToolExecutionRepository(db, principal).list_recent()
    return [
        {
            "id": r.id, "tool_name": r.tool_name, "success": r.success,
            "latency_ms": r.latency_ms, "summary": r.result_summary,
            "error": r.error, "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
