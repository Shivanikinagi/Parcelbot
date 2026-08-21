"""Repositories for state-changing artifacts: escalations and follow-up tasks."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from app.core.exceptions import AccessDeniedError
from app.models.workflow import Escalation, FollowUpTask
from app.repositories.base import ScopedRepository


class EscalationRepository(ScopedRepository):
    def _next_code(self) -> str:
        n = self.session.scalar(select(func.count(Escalation.id))) or 0
        return f"ESC-{n + 1:04d}"

    def create(
        self,
        *,
        account_id: int,
        ticket_id: int | None,
        severity: str,
        reason: str,
        assigned_to: str | None = None,
        meta: dict | None = None,
    ) -> Escalation:
        if not self.can_access_account(account_id):
            raise AccessDeniedError("Cannot escalate for an account outside your scope.")
        esc = Escalation(
            code=self._next_code(),
            account_id=account_id,
            ticket_id=ticket_id,
            created_by=self.principal.user_id,
            severity=severity,
            reason=reason,
            assigned_to=assigned_to,
            meta=meta or {},
        )
        self.session.add(esc)
        self.session.flush()
        return esc

    def list_recent(self, limit: int = 50) -> list[Escalation]:
        stmt = self.apply_account_scope(
            select(Escalation).order_by(Escalation.created_at.desc()), Escalation.account_id
        ).limit(limit)
        return list(self.session.scalars(stmt))


class FollowUpTaskRepository(ScopedRepository):
    def _next_code(self) -> str:
        n = self.session.scalar(select(func.count(FollowUpTask.id))) or 0
        return f"TASK-{n + 1:04d}"

    def create(
        self,
        *,
        title: str,
        description: str = "",
        account_id: int | None = None,
        ticket_id: int | None = None,
        due_at: datetime | None = None,
        meta: dict | None = None,
    ) -> FollowUpTask:
        if account_id is not None and not self.can_access_account(account_id):
            raise AccessDeniedError("Cannot create a task for an account outside your scope.")
        task = FollowUpTask(
            code=self._next_code(),
            account_id=account_id,
            ticket_id=ticket_id,
            created_by=self.principal.user_id,
            title=title[:240],
            description=description,
            due_at=due_at,
            meta=meta or {},
        )
        self.session.add(task)
        self.session.flush()
        return task

    def list_recent(self, limit: int = 50) -> list[FollowUpTask]:
        stmt = select(FollowUpTask).order_by(FollowUpTask.created_at.desc())
        allowed = self._scope_ids()
        if allowed is not None:
            ids = list(allowed) if allowed else [-1]
            # tasks may have null account; show those the principal created
            stmt = stmt.where(
                (FollowUpTask.account_id.in_(ids))
                | (FollowUpTask.created_by == self.principal.user_id)
            )
        return list(self.session.scalars(stmt.limit(limit)))
