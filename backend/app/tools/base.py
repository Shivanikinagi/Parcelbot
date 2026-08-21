"""Tool base classes: context, result envelope, and the safety wrapper."""

from __future__ import annotations

import time
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import AccessDeniedError, ParcelPilotError
from app.core.logging import get_logger
from app.core.security import Principal
from app.repositories.audit_repo import ToolExecutionRepository
from app.schemas.results import Citation, Conflict

logger = get_logger(__name__)


class ToolContext:
    """Everything a tool needs: a DB session, the calling principal, and trace ids.

    Repository accessors are provided so tools never touch the ORM unscoped.
    """

    def __init__(
        self,
        session: Session,
        principal: Principal,
        *,
        request_id: str | None = None,
        conversation_id: int | None = None,
        message_id: int | None = None,
    ) -> None:
        self.session = session
        self.principal = principal
        self.request_id = request_id
        self.conversation_id = conversation_id
        self.message_id = message_id

    # Lazy repository accessors (all principal-scoped).
    def accounts(self):
        from app.repositories.organization_repo import AccountRepository

        return AccountRepository(self.session, self.principal)

    def orders(self):
        from app.repositories.logistics_repo import OrderRepository

        return OrderRepository(self.session, self.principal)

    def tickets(self):
        from app.repositories.logistics_repo import TicketRepository

        return TicketRepository(self.session, self.principal)

    def agreements(self):
        from app.repositories.logistics_repo import AgreementRepository

        return AgreementRepository(self.session, self.principal)

    def knowledge(self):
        from app.repositories.knowledge_repo import KnowledgeRepository

        return KnowledgeRepository(self.session, self.principal)

    def escalations(self):
        from app.repositories.workflow_repo import EscalationRepository

        return EscalationRepository(self.session, self.principal)

    def tasks(self):
        from app.repositories.workflow_repo import FollowUpTaskRepository

        return FollowUpTaskRepository(self.session, self.principal)

    def audit(self):
        from app.repositories.audit_repo import AuditRepository

        return AuditRepository(self.session, self.principal)


class ToolResult(BaseModel):
    tool: str
    ok: bool = True
    summary: str = ""
    data: dict[str, Any] = {}
    citations: list[Citation] = []
    conflicts: list[Conflict] = []
    error: str | None = None
    requires_confirmation: bool = False
    proposed_action: dict[str, Any] | None = None
    latency_ms: int = 0


class Tool:
    """Abstract tool. Subclasses implement :meth:`run` (and :meth:`commit` if
    state-changing)."""

    name: ClassVar[str]
    description: ClassVar[str]
    input_model: ClassVar[type[BaseModel]]
    state_changing: ClassVar[bool] = False
    required_permission: ClassVar[str | None] = None

    # --- to be overridden -----------------------------------------------
    def run(self, ctx: ToolContext, args: BaseModel) -> ToolResult:  # pragma: no cover
        raise NotImplementedError

    def commit(self, ctx: ToolContext, action: dict) -> ToolResult:  # pragma: no cover
        raise NotImplementedError(f"{self.name} does not support commit")

    # --- the uniform safety wrapper -------------------------------------
    def execute(self, ctx: ToolContext, raw_args: dict[str, Any]) -> ToolResult:
        started = time.perf_counter()
        error: str | None = None
        result: ToolResult
        try:
            if self.required_permission and not ctx.principal.can(self.required_permission):
                raise AccessDeniedError(
                    f"Role '{ctx.principal.role.value}' cannot use tool '{self.name}'."
                )
            try:
                args = self.input_model(**(raw_args or {}))
            except ValidationError as exc:
                raise ParcelPilotError(f"Invalid arguments for {self.name}: {exc.errors()}") from exc
            result = self.run(ctx, args)
        except ParcelPilotError as exc:
            error = exc.message
            result = ToolResult(tool=self.name, ok=False, error=exc.message, summary=exc.message)
        except Exception as exc:  # noqa: BLE001 — contain everything, never leak
            logger.exception("Unhandled error in tool %s", self.name)
            error = "internal tool error"
            result = ToolResult(
                tool=self.name, ok=False, error="internal tool error",
                summary="The tool encountered an unexpected error.",
            )

        result.latency_ms = int((time.perf_counter() - started) * 1000)
        self._record(ctx, raw_args, result, error)
        return result

    def _record(self, ctx: ToolContext, raw_args: dict, result: ToolResult, error: str | None) -> None:
        try:
            ToolExecutionRepository(ctx.session, ctx.principal).record(
                tool_name=self.name,
                arguments=raw_args or {},
                result_summary=result.summary,
                success=result.ok,
                latency_ms=result.latency_ms,
                conversation_id=ctx.conversation_id,
                message_id=ctx.message_id,
                request_id=ctx.request_id,
                error=error,
            )
        except Exception:  # telemetry must never break the request
            logger.warning("Failed to record tool execution for %s", self.name, exc_info=True)
