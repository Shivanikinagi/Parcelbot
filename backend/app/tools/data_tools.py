"""Structured-data tools: order/ticket/agreement lookup, history, generic query.

All reads flow through principal-scoped repositories, so these tools inherit
RBAC automatically — a customer asking for another account's order simply gets a
"not found or not in your scope" result, never another account's data.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.constants import SourceType
from app.schemas.results import Citation
from app.schemas.serialize import (
    account_to_dict,
    agreement_to_dict,
    order_to_dict,
    ticket_to_dict,
)
from app.services.known_issues import match_known_issues
from app.services.severity_service import classify_severity
from app.tools.base import Tool, ToolContext, ToolResult

_STRUCTURED_CITATION = Citation(
    document_code="STRUCTURED-DATA",
    title="ParcelPilot operational database",
    heading="Structured records",
    source_type=SourceType.STRUCTURED_DATA.value,
    status="current",
    authority_rank=5,
)


def _resolve_account(ctx: ToolContext, account_code: str | None):
    """Resolve the target account, defaulting a customer to their own."""
    if account_code:
        return ctx.accounts().get_by_code(account_code)
    if ctx.principal.account_id is not None:
        return ctx.accounts().get_by_id(ctx.principal.account_id)
    return None


class OrderLookupArgs(BaseModel):
    order_code: str = Field(..., description="Order code, e.g. ORD-1001.")


class OrderLookupTool(Tool):
    name = "order_lookup"
    description = "Fetch a single shipment/order by code (RBAC-scoped)."
    input_model = OrderLookupArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: OrderLookupArgs) -> ToolResult:
        order = ctx.orders().get_by_code(args.order_code)
        if order is None:
            return ToolResult(tool=self.name, ok=False, error="not_found",
                              summary=f"Order {args.order_code} not found or not in your scope.")
        return ToolResult(
            tool=self.name, ok=True, summary=f"Order {order.code}: {order.status} via {order.carrier}.",
            data={"order": order_to_dict(order)}, citations=[_STRUCTURED_CITATION],
        )


class TicketLookupArgs(BaseModel):
    ticket_code: str = Field(..., description="Ticket code, e.g. TKT-501.")


class TicketLookupTool(Tool):
    name = "ticket_lookup"
    description = (
        "Fetch a support ticket by code (RBAC-scoped), classify its severity from the "
        "description, and flag any matching known issues."
    )
    input_model = TicketLookupArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: TicketLookupArgs) -> ToolResult:
        ticket = ctx.tickets().get_by_code(args.ticket_code)
        if ticket is None:
            return ToolResult(tool=self.name, ok=False, error="not_found",
                              summary=f"Ticket {args.ticket_code} not found or not in your scope.")
        sev = classify_severity(ticket.subject, ticket.description)
        account = ctx.accounts().get_by_id(ticket.account_id)
        known = match_known_issues(f"{ticket.subject} {ticket.description}", account.plan if account else None)
        data = ticket_to_dict(ticket)
        data["classified_severity"] = sev.model_dump()
        data["known_issues"] = known
        data["has_agreement"] = ctx.agreements().get_current_for_account(ticket.account_id) is not None
        summary = f"Ticket {ticket.code}: {sev.severity} ({sev.label}). " + (
            f"Matches {', '.join(k['code'] for k in known)}." if known else "No known-issue match."
        )
        return ToolResult(tool=self.name, ok=True, summary=summary, data=data, citations=[_STRUCTURED_CITATION])


class AgreementLookupArgs(BaseModel):
    account_code: str | None = Field(default=None, description="Account code; omit to use your own account.")


class AgreementLookupTool(Tool):
    name = "agreement_lookup"
    description = "Fetch the current signed agreement and its machine-readable terms for an account."
    input_model = AgreementLookupArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: AgreementLookupArgs) -> ToolResult:
        account = _resolve_account(ctx, args.account_code)
        if account is None:
            return ToolResult(tool=self.name, ok=False, error="account_required",
                              summary="Specify an account you have access to.")
        agreement = ctx.agreements().get_current_for_account(account.id)
        if agreement is None:
            return ToolResult(
                tool=self.name, ok=True,
                summary=f"{account.name} has no custom agreement on file; standard policies apply.",
                data={"account": account_to_dict(account), "agreement": None},
            )
        return ToolResult(
            tool=self.name, ok=True, summary=f"{account.name} agreement: {agreement.title}.",
            data={"account": account_to_dict(account), "agreement": agreement_to_dict(agreement)},
            citations=[Citation(
                document_code=agreement.code, title=agreement.title, heading="Agreement terms",
                source_type="customer_agreement", status="current", authority_rank=1,
                source_file=agreement.source_file,
            )],
        )


class CustomerHistoryArgs(BaseModel):
    account_code: str | None = Field(default=None, description="Account code; omit to use your own account.")


class CustomerHistoryTool(Tool):
    name = "customer_history"
    description = "List an account's orders and tickets (including historical/closed) — RBAC-scoped."
    input_model = CustomerHistoryArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: CustomerHistoryArgs) -> ToolResult:
        account = _resolve_account(ctx, args.account_code)
        if account is None:
            return ToolResult(tool=self.name, ok=False, error="account_required",
                              summary="Specify an account you have access to.")
        orders = ctx.orders().list_for_account(account.id)
        tickets = ctx.tickets().list_for_account(account.id)
        return ToolResult(
            tool=self.name, ok=True,
            summary=f"{account.name}: {len(orders)} order(s), {len(tickets)} ticket(s).",
            data={
                "account": account_to_dict(account),
                "orders": [order_to_dict(o) for o in orders],
                "tickets": [ticket_to_dict(t) for t in tickets],
            },
            citations=[_STRUCTURED_CITATION],
        )


class StructuredQueryArgs(BaseModel):
    entity: Literal["orders", "tickets", "accounts"]
    account_code: str | None = None
    status: str | None = Field(default=None, description="Optional status filter.")


class StructuredDataQueryTool(Tool):
    name = "structured_data_query"
    description = (
        "Generic structured query over orders/tickets/accounts with optional account and "
        "status filters. Always RBAC-scoped."
    )
    input_model = StructuredQueryArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: StructuredQueryArgs) -> ToolResult:
        if args.entity == "accounts":
            rows = ctx.accounts().list_accounts()
            data = [account_to_dict(a) for a in rows]
        elif args.entity == "orders":
            acct = _resolve_account(ctx, args.account_code)
            rows = ctx.orders().list_for_account(acct.id) if acct else ctx.orders().list_all()
            data = [order_to_dict(o) for o in rows]
        else:  # tickets
            acct = _resolve_account(ctx, args.account_code)
            rows = ctx.tickets().list_for_account(acct.id) if acct else ctx.tickets().list_all()
            data = [ticket_to_dict(t) for t in rows]

        if args.status:
            data = [d for d in data if str(d.get("status", "")).lower() == args.status.lower()]
        return ToolResult(
            tool=self.name, ok=True, summary=f"{len(data)} {args.entity} row(s).",
            data={"entity": args.entity, "rows": data}, citations=[_STRUCTURED_CITATION],
        )
