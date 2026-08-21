"""State-changing tools: escalation, follow-up task, ticket update.

Two-phase safety contract:
    * ``run`` (prepare) NEVER mutates. It validates inputs, checks scope, and
      returns ``requires_confirmation=True`` with a ``proposed_action`` that spells
      out exactly what will change and the consequences.
    * ``commit`` performs the mutation and writes an audit-log entry. It is only
      reached after the user explicitly confirms (via the /chat/confirm endpoint),
      which re-validates permission and scope.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.clock import reference_now
from app.core.exceptions import NotFoundError
from app.tools.base import Tool, ToolContext, ToolResult


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------
class EscalationArgs(BaseModel):
    ticket_code: str = Field(..., description="Ticket to escalate, e.g. TKT-501.")
    severity: Literal["P1", "P2", "P3"] | None = None
    reason: str | None = Field(default=None, description="Why escalation is warranted.")


class EscalationCreatorTool(Tool):
    name = "escalation_creator"
    description = (
        "Create an escalation for a ticket (e.g. a breached P1 SLA). State-changing: "
        "prepares a confirmation first, then commits on approval."
    )
    input_model = EscalationArgs
    state_changing = True

    def run(self, ctx: ToolContext, args: EscalationArgs) -> ToolResult:
        ticket = ctx.tickets().get_by_code(args.ticket_code)
        if ticket is None:
            raise NotFoundError(f"Ticket {args.ticket_code} not found or not in your scope.")
        account = ctx.accounts().get_by_id(ticket.account_id)
        severity = args.severity or ticket.severity or "P2"
        reason = args.reason or f"{severity} ticket {ticket.code} requires escalation."
        assigned_to = account.csm or "On-call manager"
        action = {
            "tool": self.name,
            "human": f"Escalate {ticket.code} ({account.name}) at {severity} to {assigned_to}.",
            "consequences": [
                "Creates a new escalation record visible to the operations team.",
                f"Notifies the assigned owner ({assigned_to}).",
                "Writes an entry to the audit log.",
            ],
            "params": {
                "ticket_code": ticket.code,
                "account_code": account.code,
                "severity": severity,
                "reason": reason,
                "assigned_to": assigned_to,
            },
        }
        return ToolResult(
            tool=self.name, ok=True, requires_confirmation=True, proposed_action=action,
            summary=action["human"],
        )

    def commit(self, ctx: ToolContext, action: dict) -> ToolResult:
        params = action["params"]
        account = ctx.accounts().get_by_code(params["account_code"])
        ticket = ctx.tickets().get_by_code(params["ticket_code"])
        if account is None or ticket is None:
            raise NotFoundError("Referenced account/ticket is not in your scope.")
        esc = ctx.escalations().create(
            account_id=account.id, ticket_id=ticket.id, severity=params["severity"],
            reason=params["reason"], assigned_to=params.get("assigned_to"),
            meta={"source": "agent"},
        )
        ctx.audit().record(
            action="create_escalation", resource_type="escalation", resource_id=esc.code,
            account_id=account.id, details=params, request_id=ctx.request_id,
        )
        return ToolResult(tool=self.name, ok=True,
                          summary=f"Escalation {esc.code} created for {ticket.code}.",
                          data={"escalation_code": esc.code})


# ---------------------------------------------------------------------------
# Follow-up task
# ---------------------------------------------------------------------------
class TaskArgs(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = ""
    account_code: str | None = None
    ticket_code: str | None = None
    due_in_hours: int | None = Field(default=None, ge=1, le=720)


class FollowUpTaskCreatorTool(Tool):
    name = "follow_up_task_creator"
    description = "Create a follow-up task/action item. State-changing; confirmed before commit."
    input_model = TaskArgs
    state_changing = True
    required_permission = "create_task"

    def run(self, ctx: ToolContext, args: TaskArgs) -> ToolResult:
        account = ctx.accounts().get_by_code(args.account_code) if args.account_code else None
        due_desc = f"in {args.due_in_hours}h" if args.due_in_hours else "no due date"
        action = {
            "tool": self.name,
            "human": f"Create follow-up task: '{args.title}' ({due_desc}).",
            "consequences": ["Creates a task in the ops queue.", "Writes an audit-log entry."],
            "params": {
                "title": args.title, "description": args.description,
                "account_code": account.code if account else None,
                "ticket_code": args.ticket_code, "due_in_hours": args.due_in_hours,
            },
        }
        return ToolResult(tool=self.name, ok=True, requires_confirmation=True,
                          proposed_action=action, summary=action["human"])

    def commit(self, ctx: ToolContext, action: dict) -> ToolResult:
        params = action["params"]
        account = ctx.accounts().get_by_code(params["account_code"]) if params.get("account_code") else None
        ticket = ctx.tickets().get_by_code(params["ticket_code"]) if params.get("ticket_code") else None
        due_at = None
        if params.get("due_in_hours"):
            from datetime import timedelta
            due_at = reference_now() + timedelta(hours=int(params["due_in_hours"]))
        task = ctx.tasks().create(
            title=params["title"], description=params.get("description", ""),
            account_id=account.id if account else None,
            ticket_id=ticket.id if ticket else None, due_at=due_at, meta={"source": "agent"},
        )
        ctx.audit().record(
            action="create_follow_up_task", resource_type="task", resource_id=task.code,
            account_id=account.id if account else None, details=params, request_id=ctx.request_id,
        )
        return ToolResult(tool=self.name, ok=True, summary=f"Task {task.code} created.",
                          data={"task_code": task.code})


# ---------------------------------------------------------------------------
# Ticket update
# ---------------------------------------------------------------------------
class TicketUpdateArgs(BaseModel):
    ticket_code: str = Field(...)
    status: str | None = None
    severity: Literal["P1", "P2", "P3"] | None = None
    assigned_to: str | None = None

    def has_change(self) -> bool:
        return any([self.status, self.severity, self.assigned_to])


class TicketUpdateTool(Tool):
    name = "ticket_update"
    description = "Update a ticket's status/severity/assignee. State-changing; confirmed before commit."
    input_model = TicketUpdateArgs
    state_changing = True
    required_permission = "update_ticket"

    def run(self, ctx: ToolContext, args: TicketUpdateArgs) -> ToolResult:
        if not args.has_change():
            return ToolResult(tool=self.name, ok=False, error="no_change",
                              summary="Specify at least one of status, severity, or assignee.")
        ticket = ctx.tickets().get_by_code(args.ticket_code)
        if ticket is None:
            raise NotFoundError(f"Ticket {args.ticket_code} not found or not in your scope.")
        changes = {}
        if args.status and args.status != ticket.status:
            changes["status"] = {"from": ticket.status, "to": args.status}
        if args.severity and args.severity != ticket.severity:
            changes["severity"] = {"from": ticket.severity, "to": args.severity}
        if args.assigned_to and args.assigned_to != ticket.assigned_to:
            changes["assigned_to"] = {"from": ticket.assigned_to, "to": args.assigned_to}
        action = {
            "tool": self.name,
            "human": f"Update {ticket.code}: " + ", ".join(f"{k} {v['from']}→{v['to']}" for k, v in changes.items()),
            "consequences": ["Modifies the ticket record.", "Writes an audit-log entry."],
            "params": {"ticket_code": ticket.code, "changes": changes},
        }
        return ToolResult(tool=self.name, ok=True, requires_confirmation=True,
                          proposed_action=action, summary=action["human"])

    def commit(self, ctx: ToolContext, action: dict) -> ToolResult:
        params = action["params"]
        ticket = ctx.tickets().get_by_code(params["ticket_code"])
        if ticket is None:
            raise NotFoundError("Ticket not found or not in your scope.")
        for field, change in params["changes"].items():
            setattr(ticket, field, change["to"])
        ctx.session.flush()
        ctx.audit().record(
            action="update_ticket", resource_type="ticket", resource_id=ticket.code,
            account_id=ticket.account_id, details=params, request_id=ctx.request_id,
        )
        return ToolResult(tool=self.name, ok=True, summary=f"Ticket {ticket.code} updated.",
                          data={"ticket_code": ticket.code, "changes": params["changes"]})
