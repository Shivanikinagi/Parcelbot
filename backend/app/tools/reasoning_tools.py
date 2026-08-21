"""Reasoning tools that expose the deterministic business-rule services.

These return fully-explained, citation- and conflict-bearing results. The agent
combines them with retrieved evidence; the LLM only narrates what these compute.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.services.cancellation_service import evaluate_cancellation
from app.services.service_credit_service import (
    evaluate_service_credit,
    evaluate_service_credit_scenario,
)
from app.services.severity_service import classify_severity
from app.services.sla_service import compute_sla
from app.tools.base import Tool, ToolContext, ToolResult


class SLAArgs(BaseModel):
    ticket_code: str | None = Field(default=None, description="Compute SLA for this ticket.")
    account_code: str | None = Field(default=None, description="Account (with severity) if no ticket.")
    severity: Literal["P1", "P2", "P3"] | None = None

    @model_validator(mode="after")
    def _need_input(self):
        if not self.ticket_code and not (self.account_code and self.severity):
            raise ValueError("Provide either ticket_code, or both account_code and severity.")
        return self


class SLACalculatorTool(Tool):
    name = "sla_calculator"
    description = (
        "Compute the first-response SLA target, elapsed time, and breach status for a "
        "ticket (or account+severity), resolving agreement vs policy precedence and "
        "surfacing any conflict."
    )
    input_model = SLAArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: SLAArgs) -> ToolResult:
        if args.ticket_code:
            ticket = ctx.tickets().get_by_code(args.ticket_code)
            if ticket is None:
                return ToolResult(tool=self.name, ok=False, error="not_found",
                                  summary=f"Ticket {args.ticket_code} not found or not in your scope.")
            account = ctx.accounts().get_by_id(ticket.account_id)
            severity = args.severity or ticket.severity or classify_severity(ticket.subject, ticket.description).severity
            created = ticket.business_created_at
        else:
            account = ctx.accounts().get_by_code(args.account_code)
            if account is None:
                return ToolResult(tool=self.name, ok=False, error="not_found",
                                  summary="Account not found or not in your scope.")
            severity = args.severity
            from app.core.clock import reference_now
            created = reference_now()

        agreement = ctx.agreements().get_current_for_account(account.id)
        sla = compute_sla(account, agreement, severity, created)
        return ToolResult(
            tool=self.name, ok=True, summary=sla.explanation,
            data={"sla": sla.model_dump(mode="json")},
            citations=sla.citations, conflicts=sla.conflicts,
        )


class OrderRefArgs(BaseModel):
    order_code: str = Field(..., description="Order code, e.g. ORD-2002.")


class CancellationEvaluatorTool(Tool):
    name = "cancellation_evaluator"
    description = (
        "Assess whether an order may be cancelled and any fee, applying SOP v4 §1, the "
        "30-minute window, status rules, and agreement fee waivers. Advisory (read-only)."
    )
    input_model = OrderRefArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: OrderRefArgs) -> ToolResult:
        order = ctx.orders().get_by_code(args.order_code)
        if order is None:
            return ToolResult(tool=self.name, ok=False, error="not_found",
                              summary=f"Order {args.order_code} not found or not in your scope.")
        account = ctx.accounts().get_by_id(order.account_id)
        agreement = ctx.agreements().get_current_for_account(order.account_id)
        result = evaluate_cancellation(order, account, agreement)
        return ToolResult(
            tool=self.name, ok=True, summary=result.reason,
            data={"cancellation": result.model_dump(mode="json")},
            citations=result.citations, conflicts=result.conflicts,
        )


class ServiceCreditScenarioArgs(BaseModel):
    delay_hours: float = Field(..., gt=0, le=72, description="How many hours past the pickup window, as described by the user.")
    carrier_fault: bool = Field(default=False, description="Whether the user attributed the delay to carrier fault.")
    customer_fault: bool = Field(default=False, description="Whether a customer-caused issue was mentioned.")
    account_code: str | None = Field(default=None, description="Account code; omit to use the caller's own account.")


class ServiceCreditScenarioTool(Tool):
    name = "service_credit_scenario_evaluator"
    description = (
        "Assess failed-pickup service-credit eligibility from a described scenario (a delay "
        "length and fault attribution given in natural language) against the caller's account "
        "contract, for hypothetical questions that don't name a specific order."
    )
    input_model = ServiceCreditScenarioArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: ServiceCreditScenarioArgs) -> ToolResult:
        account = None
        if args.account_code:
            account = ctx.accounts().get_by_code(args.account_code)
        elif ctx.principal.account_id is not None:
            account = ctx.accounts().get_by_id(ctx.principal.account_id)
        if account is None:
            return ToolResult(
                tool=self.name, ok=False, error="account_required",
                summary="I need an account to check contract terms against — please specify one.",
            )
        agreement = ctx.agreements().get_current_for_account(account.id)
        result = evaluate_service_credit_scenario(
            account, agreement, delay_hours=args.delay_hours,
            carrier_fault=args.carrier_fault, customer_fault=args.customer_fault,
        )
        return ToolResult(
            tool=self.name, ok=True, summary=result.reason,
            data={"service_credit_scenario": result.model_dump(mode="json")},
            citations=result.citations, conflicts=result.conflicts,
        )


class ServiceCreditEvaluatorTool(Tool):
    name = "service_credit_evaluator"
    description = (
        "Assess failed-pickup service-credit eligibility and amount, applying SOP v4 §2/§3 "
        "and agreement overrides, with the 'do not promise when uncertain' guardrail. Advisory."
    )
    input_model = OrderRefArgs
    required_permission = "read_own"

    def run(self, ctx: ToolContext, args: OrderRefArgs) -> ToolResult:
        order = ctx.orders().get_by_code(args.order_code)
        if order is None:
            return ToolResult(tool=self.name, ok=False, error="not_found",
                              summary=f"Order {args.order_code} not found or not in your scope.")
        account = ctx.accounts().get_by_id(order.account_id)
        agreement = ctx.agreements().get_current_for_account(order.account_id)
        result = evaluate_service_credit(order, account, agreement)
        return ToolResult(
            tool=self.name, ok=True, summary=result.reason,
            data={"service_credit": result.model_dump(mode="json")},
            citations=result.citations, conflicts=result.conflicts,
        )
