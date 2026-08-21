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

_NUMBER_WORDS = {
    "half": 0.5, "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_HOURS_RE = re.compile(
    r"\b(?:(?P<num>\d+(?:\.\d+)?)|(?P<word>half|a|an|one|two|three|four|five|six|seven|eight|nine|ten))"
    r"\s*(?:hours?|hrs?|h)\b",
    re.IGNORECASE,
)
_CARRIER_FAULT_RE = re.compile(
    r"carrier(?:'s)?\s+fault|carrier\s+(?:is|was)\s+at\s+fault|fault\s+of\s+the\s+carrier|"
    r"(?:due|because)\s+(?:to|of)\s+(?:the\s+)?carrier",
    re.IGNORECASE,
)
_CUSTOMER_FAULT_RE = re.compile(
    r"\b(?:my|our|the\s+customer(?:'s)?)\s+fault\b|customer[- ]caused",
    re.IGNORECASE,
)


def extract_scenario_params(query: str) -> dict | None:
    """Pull a hypothetical delay/fault scenario out of free text, if present.

    Powers hypothetical questions with no order code — e.g. "my pickup was
    three hours late because of carrier fault, do I get a credit?" — by giving
    the planner enough structured signal to run the real eligibility rule
    against the caller's account instead of just citing the policy text.
    """
    m = _HOURS_RE.search(query)
    if not m:
        return None
    if m.group("num"):
        hours = float(m.group("num"))
    else:
        hours = _NUMBER_WORDS.get(m.group("word").lower())
        if hours is None:
            return None
    carrier_fault = bool(_CARRIER_FAULT_RE.search(query))
    customer_fault = bool(_CUSTOMER_FAULT_RE.search(query))
    if not carrier_fault and not customer_fault:
        return None  # not enough signal to reason about fault-based eligibility
    return {"delay_hours": hours, "carrier_fault": carrier_fault, "customer_fault": customer_fault}


def _norm(code: str) -> str:
    return code.upper().replace("ORD", "ORD-").replace("TKT", "TKT-").replace("ACCT", "ACCT-").replace("--", "-")


def extract_entities(query: str) -> dict:
    return {
        "orders": sorted({_norm(m.group()) for m in _ORDER_RE.finditer(query)}),
        "tickets": sorted({_norm(m.group()) for m in _TICKET_RE.finditer(query)}),
        "accounts": sorted({_norm(m.group()) for m in _ACCOUNT_RE.finditer(query)}),
    }


def carry_forward_entities(current: dict, history: list[dict]) -> tuple[dict, bool]:
    """Fill in any empty entity slot from the most recent prior turn that had one.

    Powers natural follow-ups like "why did you choose that SLA?" — with no
    ticket code restated, the current turn's own extraction is empty, but the
    ticket discussed one turn ago should still be in play. Returns the
    (possibly-filled) entities and whether anything was actually carried over,
    so the caller can note it in the reasoning trace.
    """
    filled = {k: list(v) for k, v in current.items()}
    carried = False
    for msg in reversed(history):
        content = msg.get("content", "")
        if not content:
            continue
        prior = extract_entities(content)
        for key in ("tickets", "orders", "accounts"):
            if not filled[key] and prior[key]:
                filled[key] = prior[key]
                carried = True
        if all(filled[key] for key in ("tickets", "orders", "accounts")):
            break
    return filled, carried


_INTENT_SIGNALS: list[tuple[str, str]] = [
    ("action_cancel_request", r"^\s*(actually[, ]+)?(don'?t|do not|no,? )\s*(do (that|it)|proceed|escalate)\b|"
                               r"\b(never\s?mind|belay that|cancel that|abort that|scratch that)\b"),
    ("action_escalate", r"\bescalat"),
    ("action_task", r"\b(follow[- ]?up task|create (a )?task|remind me|add a todo|action item)\b"),
    ("action_update", r"\b(update|set|change|assign|close|resolve|mark)\b.*\b(ticket|status|severity|priority)\b|\bmark .* (resolved|closed)\b"),
    ("cancellation", r"\bcancel"),
    ("service_credit", r"\b(service credit|credit|refund|compensat|failed pickup|missed pickup)\b"),
    ("analytics", r"\b(analy[sz]e|analytics|cluster|trend|recurring|unusual pattern|urgent issues?|"
                  r"multiple customers|which (accounts|tickets|orders)|same (known )?issue|approaching.*sla|"
                  r"exceeding.*sla|breach\w*.*(sla|target)|summary of support|overview of (support|ticket|operations)|"
                  r"support activity|breakdown (by|of)|most (frequent|urgent)|highest number of|"
                  r"top (issue|customer|\d+|three)|carrier failures?)\b"),
    ("sla", r"\b(sla|response time|first response|breach|target|how long|deadline)\b"),
    ("triage", r"\b(severity|triage|priorit|classify|what.*priority|how bad)\b"),
    ("audit", r"\baudit\b"),
    ("history", r"\b(history|past ticket|previous ticket|earlier|prior)\b"),
    ("help", r"^\s*(what can you( help| do)|can you help|how can you help|help me\b(?!.{0,10}\b(order|pickup|ticket|shipment))|"
             r"what (do you|can this) do)\b"),
    ("greeting", r"^\s*(hi|hello|hey|thanks|thank you|good (morning|afternoon))\b"),
]

_VAGUE_PROBLEM_RE = re.compile(
    r"\b(problem|issue|trouble)\s+with\s+(my|the)\s+(pickup|order|shipment|delivery|package|parcel)\b",
    re.IGNORECASE,
)

# Distinguishes "what IS the [general] SLA policy" (answerable generically) from
# "is THIS ticket/account breaching SLA" (needs a specific target to compute).
_SLA_COMPUTE_RE = re.compile(
    r"\b(breach\w*|overdue|exceed\w*|remaining|elapsed|is it|has it|my (ticket|sla|account)|this ticket|"
    r"still (within|on) target)\b",
    re.IGNORECASE,
)


def classify_intent(query: str, entities: dict) -> dict:
    q = query.lower()
    # A named ticket/order is a per-record question ("has TKT-501 breached?"),
    # never the aggregate/cross-record question analytics phrasing implies —
    # keep it on the specific-record path even if the wording overlaps.
    has_specific_entity = bool(entities.get("tickets") or entities.get("orders"))
    matched = None
    for name, pattern in _INTENT_SIGNALS:
        if name == "analytics" and has_specific_entity:
            continue
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


def detect_clarification(intent: dict, entities: dict, principal: Principal) -> str | None:
    """Return a clarifying question when a request can't be safely acted on
    as-is, instead of silently falling through to an unrelated document search.
    """
    itype = intent["type"]
    query = intent["raw"]
    ticket = entities["tickets"][0] if entities["tickets"] else None
    order = entities["orders"][0] if entities["orders"] else None
    has_account_context = bool(entities["accounts"]) or principal.account_id is not None

    if itype == "action_escalate" and not ticket:
        return "Which ticket would you like me to escalate? Please give me a ticket code (e.g. TKT-501)."
    if itype == "action_update" and not ticket:
        return "Which ticket would you like to update, and what should change (status, severity, or assignee)?"
    if itype == "action_task" and len(query.split()) <= 4:
        return "What should the follow-up task be about, and for which ticket or account (if any)?"
    if itype == "sla" and not ticket and not has_account_context and _SLA_COMPUTE_RE.search(query):
        return "Which ticket or account would you like the SLA target for?"
    if itype == "cancellation" and not order and not has_account_context:
        return "Which order would you like to check for cancellation — do you have the order code (e.g. ORD-1001)?"
    if _VAGUE_PROBLEM_RE.search(query) and not order and not ticket:
        return "Sorry to hear that — could you share the order code (e.g. ORD-1001) and what happened with the pickup?"
    return None


def _default_account_arg(principal: Principal, entities: dict) -> dict:
    """Prefer an explicit in-query account (internal), else the caller's own."""
    if entities["accounts"] and principal.role.is_internal:
        return {"account_code": entities["accounts"][0]}
    return {}


def _analytics_focus(query: str) -> str:
    q = query.lower()
    if re.search(r"cluster|same.*issue|underlying issue", q):
        return "clusters"
    if re.search(r"approaching|exceeding|breach|sla risk|urgent|which tickets", q):
        return "sla_risk"
    if re.search(r"multiple customers|which accounts|affected", q):
        return "cross_customer"
    if re.search(r"overview|breakdown|by severity|severity and|summary of support", q):
        return "summary"
    return "insights"


def plan_tools(
    intent: dict,
    entities: dict,
    principal: Principal,
    context_account_id: int | None = None,
) -> list[PlannedCall]:
    itype = intent["type"]
    plan: list[PlannedCall] = []
    query = intent["raw"]
    ticket = entities["tickets"][0] if entities["tickets"] else None
    order = entities["orders"][0] if entities["orders"] else None

    def add(tool, args, phase, why):
        plan.append(PlannedCall(tool=tool, args=args, phase=phase, why=why))

    if itype in {"greeting", "help", "action_cancel_request"}:
        return plan  # no tools; the narrator handles a canned, deterministic reply

    if itype == "analytics":
        add(
            "analytics_tool", {"focus": _analytics_focus(query)}, "structured",
            "Pull live, data-backed proactive insights instead of citing static policy text.",
        )
        return plan

    if itype == "audit":
        add("audit_log", {}, "structured", "Read the immutable audit trail of recent state-changing actions.")
        return plan

    # Almost everything benefits from grounding in the knowledge base.
    if itype not in {"action_task"}:
        add(
            "document_search", {"query": query, "context_account_id": context_account_id}, "retrieve",
            "Ground the answer in policy/SOP/agreement evidence.",
        )

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
    elif itype == "service_credit":
        # No order named — try to reason over a described scenario instead of
        # only citing the policy text (see extract_scenario_params).
        scenario = extract_scenario_params(query)
        if scenario:
            args = dict(scenario)
            if entities["accounts"] and principal.role.is_internal:
                args["account_code"] = entities["accounts"][0]
            add(
                "service_credit_scenario_evaluator", args, "structured",
                "Assess eligibility from the described delay/fault against the account's contract terms.",
            )
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
