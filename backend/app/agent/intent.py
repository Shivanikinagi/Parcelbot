"""Intent classification and deterministic tool planning.

Rule-based and transparent: the same query always yields the same plan, which
is exactly what you want for an auditable support agent. Entities (order/ticket/
account codes) are extracted with regex; intent is chosen from keyword signals.
The planner maps (intent, entities, role) to an ordered list of tool calls
grouped into retrieve / structured / action phases.
"""

from __future__ import annotations

import re

from app.agent.state import PlannedCall
from app.core.security import Principal

_ORDER_RE = re.compile(r"\bORD-?\d+\b", re.IGNORECASE)
_TICKET_RE = re.compile(r"\bTKT-?\d+\b", re.IGNORECASE)
_ACCOUNT_RE = re.compile(r"\bACCT-?\d+\b", re.IGNORECASE)


def _norm(code: str) -> str:
    return code.upper().replace("ORD", "ORD-").replace("TKT", "TKT-").replace("ACCT", "ACCT-").replace("--", "-")


def extract_entities(query: str) -> dict:
    return {
        "orders": sorted({_norm(m.group()) for m in _ORDER_RE.finditer(query)}),
        "tickets": sorted({_norm(m.group()) for m in _TICKET_RE.finditer(query)}),
        "accounts": sorted({_norm(m.group()) for m in _ACCOUNT_RE.finditer(query)}),
    }


_INTENT_SIGNALS: list[tuple[str, str]] = [
    ("action_escalate", r"\bescalat"),
    ("action_task", r"\b(follow[- ]?up task|create (a )?task|remind me|add a todo|action item)\b"),
    ("action_update", r"\b(update|set|change|assign|close|resolve|mark)\b.*\b(ticket|status|severity|priority)\b|\bmark .* (resolved|closed)\b"),
    ("cancellation", r"\bcancel"),
    ("service_credit", r"\b(service credit|credit|refund|compensat|failed pickup|missed pickup)\b"),
    ("sla", r"\b(sla|response time|first response|breach|target|how long|deadline)\b"),
    ("triage", r"\b(severity|triage|priorit|classify|what.*priority|how bad)\b"),
    ("history", r"\b(history|past ticket|previous ticket|earlier|prior)\b"),
    ("greeting", r"^\s*(hi|hello|hey|thanks|thank you|good (morning|afternoon))\b"),
]


def classify_intent(query: str, entities: dict) -> dict:
    q = query.lower()
    matched = None
    for name, pattern in _INTENT_SIGNALS:
        if re.search(pattern, q, re.IGNORECASE):
            matched = name
            break
    if matched is None:
        matched = "knowledge" if len(q.split()) > 2 else "general"
    return {
        "type": matched,
        "is_action": matched.startswith("action_"),
        "raw": query,
    }


def _default_account_arg(principal: Principal, entities: dict) -> dict:
    """Prefer an explicit in-query account (internal), else the caller's own."""
    if entities["accounts"] and principal.role.is_internal:
        return {"account_code": entities["accounts"][0]}
    return {}


def plan_tools(intent: dict, entities: dict, principal: Principal) -> list[PlannedCall]:
    itype = intent["type"]
    plan: list[PlannedCall] = []
    query = intent["raw"]
    ticket = entities["tickets"][0] if entities["tickets"] else None
    order = entities["orders"][0] if entities["orders"] else None

    def add(tool, args, phase, why):
        plan.append(PlannedCall(tool=tool, args=args, phase=phase, why=why))

    if itype == "greeting":
        return plan  # no tools; the narrator handles a friendly reply

    # Almost everything benefits from grounding in the knowledge base.
    if itype not in {"action_task"}:
        add("document_search", {"query": query}, "retrieve", "Ground the answer in policy/SOP/agreement evidence.")

    # Known-issue matching where relevant.
    if itype in {"triage", "knowledge", "general"} or ticket:
        add("known_issue_match", {"text": query}, "retrieve", "Check for a matching current known issue.")

    # Structured lookups.
    if ticket:
        add("ticket_lookup", {"ticket_code": ticket}, "structured", "Load the ticket and classify severity.")
    if order:
        add("order_lookup", {"order_code": order}, "structured", "Load the referenced order.")

    if itype == "sla" and ticket:
        add("sla_calculator", {"ticket_code": ticket}, "structured", "Compute the SLA target and breach status.")
    if itype == "triage" and ticket:
        add("sla_calculator", {"ticket_code": ticket}, "structured", "Attach the SLA to the triage.")
    if itype == "cancellation" and order:
        add("cancellation_evaluator", {"order_code": order}, "structured", "Assess cancellation eligibility and fee.")
    if itype == "service_credit" and order:
        add("service_credit_evaluator", {"order_code": order}, "structured", "Assess service-credit eligibility.")
    if itype == "history":
        add("customer_history", _default_account_arg(principal, entities), "structured", "Pull account order/ticket history.")
    if itype in {"sla", "knowledge", "general"} and not ticket and (entities["accounts"] or principal.account_id):
        # e.g. "what's my SLA?" — fetch the agreement for context.
        add("agreement_lookup", _default_account_arg(principal, entities), "structured", "Load the applicable agreement terms.")

    # State-changing actions (prepared, not executed).
    if itype == "action_escalate" and ticket:
        add("sla_calculator", {"ticket_code": ticket}, "structured", "Justify the escalation with SLA status.")
        add("escalation_creator", {"ticket_code": ticket}, "action", "Prepare an escalation for confirmation.")
    if itype == "action_task":
        add("follow_up_task_creator", {"title": query[:120]}, "action", "Prepare a follow-up task for confirmation.")
    if itype == "action_update" and ticket:
        # Parse a target status/severity from the text if present.
        args: dict = {"ticket_code": ticket}
        m = re.search(r"\b(open|in_progress|pending_customer|escalated|resolved|closed)\b", query, re.IGNORECASE)
        if m:
            args["status"] = m.group(1).lower()
        sev = re.search(r"\bP([123])\b", query)
        if sev:
            args["severity"] = f"P{sev.group(1)}"
        add("ticket_update", args, "action", "Prepare a ticket update for confirmation.")

    return plan
