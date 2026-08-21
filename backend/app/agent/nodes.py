"""LangGraph node implementations.

Each node is a pure-ish function ``AgentState -> partial AgentState``. Nodes
add to the reasoning ``trace`` so the UI can render a high-level timeline of the
agent's decisions.
"""

from __future__ import annotations

from app.agent.intent import classify_intent, extract_entities, plan_tools
from app.agent.state import AgentState, add_trace
from app.core.constants import Confidence
from app.core.logging import get_logger
from app.tools import registry
from app.tools.base import ToolResult

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _collect(state: AgentState, result: ToolResult) -> None:
    state.setdefault("tool_calls", []).append(
        {
            "tool": result.tool,
            "ok": result.ok,
            "summary": result.summary,
            "latency_ms": result.latency_ms,
            "requires_confirmation": result.requires_confirmation,
            "error": result.error,
        }
    )
    state.setdefault("results", {})[result.tool] = result
    for c in result.citations:
        state.setdefault("citations", []).append(c.model_dump())
    for cf in result.conflicts:
        state.setdefault("conflicts", []).append(cf.model_dump())


def _run_phase(state: AgentState, phase: str) -> None:
    ctx = state["ctx"]
    for call in state.get("plan", []):
        if call["phase"] != phase:
            continue
        tool = registry.get_tool(call["tool"])
        if tool is None:
            continue
        result = tool.execute(ctx, call["args"])
        _collect(state, result)


def _dedupe_citations(citations: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for c in citations:
        key = (c.get("document_code"), c.get("heading"))
        if key not in seen or c.get("relevance", 0) > seen[key].get("relevance", 0):
            seen[key] = c
    ordered = sorted(seen.values(), key=lambda c: (c.get("authority_rank", 9), -c.get("relevance", 0)))
    for i, c in enumerate(ordered, start=1):
        c["marker"] = f"S{i}"
    return ordered


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------
def intent_classification(state: AgentState) -> AgentState:
    if state.get("confirm_action"):
        state["intent"] = {"type": "confirm", "is_action": True, "raw": state["query"]}
        add_trace(state, "intent", "Confirmation", "Executing a previously prepared, user-approved action.")
        return state
    entities = extract_entities(state["query"])
    intent = classify_intent(state["query"], entities)
    state["entities"] = entities
    state["intent"] = intent
    ents = ", ".join(v for grp in entities.values() for v in grp) or "none"
    add_trace(state, "intent", f"Intent: {intent['type']}", f"Entities: {ents}")
    return state


def authorization(state: AgentState) -> AgentState:
    principal = state["ctx"].principal
    if not principal.can("chat"):
        state["error"] = "Your role is not permitted to use the assistant."
    add_trace(
        state, "authorization",
        f"Authorized as {principal.role.value}",
        "Data access is scoped to " + ("all accounts" if principal.role.is_privileged
                                        else "your own/assigned accounts") + ".",
    )
    return state


def planner(state: AgentState) -> AgentState:
    if state.get("confirm_action") or state.get("error"):
        state["plan"] = []
        return state
    plan = plan_tools(state["intent"], state["entities"], state["ctx"].principal)
    state["plan"] = plan
    steps = " → ".join(c["tool"] for c in plan) or "direct answer"
    add_trace(state, "planner", f"Planned {len(plan)} tool call(s)", steps)
    return state


def retriever(state: AgentState) -> AgentState:
    if not state.get("plan"):
        return state
    _run_phase(state, "retrieve")
    doc = state.get("results", {}).get("document_search")
    if doc:
        add_trace(state, "retriever", "Evidence retrieved",
                  f"{len(doc.data.get('passages', []))} passage(s), confidence {doc.data.get('confidence', 0):.2f}")
    return state


def structured_data(state: AgentState) -> AgentState:
    if not state.get("plan"):
        return state
    _run_phase(state, "structured")
    tools = [c["tool"] for c in state["plan"] if c["phase"] == "structured"]
    if tools:
        add_trace(state, "structured_data", "Structured data queried", ", ".join(tools))
    return state


def reasoner(state: AgentState) -> AgentState:
    """Synthesise structured facts + evidence into an explainable draft."""
    results: dict[str, ToolResult] = state.get("results", {})
    key_facts: list[str] = []
    evidence: list[dict] = []

    if "sla_calculator" in results and results["sla_calculator"].ok:
        sla = results["sla_calculator"].data["sla"]
        key_facts.append(
            f"SLA target {sla['target_human']} (source: {sla['source'].replace('_', ' ')}); "
            + ("BREACHED" if sla["breached"] else f"{max(0, sla['remaining_minutes'])} min remaining")
            + f" — elapsed {sla['elapsed_human']}."
        )
        evidence.append({"kind": "computation", "label": "SLA", "detail": sla["explanation"]})
    if "cancellation_evaluator" in results and results["cancellation_evaluator"].ok:
        c = results["cancellation_evaluator"].data["cancellation"]
        key_facts.append(
            f"Cancellation: {'allowed' if c['allowed'] else 'not allowed'}"
            + (f", fee INR {c['fee_inr']:.0f}" if c["allowed"] else "")
            + (f" — {c['recommended_action']}" if c.get("recommended_action") else "") + "."
        )
        evidence.append({"kind": "computation", "label": "Cancellation", "detail": c["reason"]})
    if "service_credit_evaluator" in results and results["service_credit_evaluator"].ok:
        c = results["service_credit_evaluator"].data["service_credit"]
        key_facts.append(
            f"Service credit: {'eligible for INR ' + format(c['amount_inr'], '.0f') if c['eligible'] else 'not eligible'}"
            + (" (manager approval required)" if c.get("requires_manager_approval") else "") + "."
        )
        evidence.append({"kind": "computation", "label": "Service credit", "detail": c["reason"]})
    if "service_credit_scenario_evaluator" in results and results["service_credit_scenario_evaluator"].ok:
        c = results["service_credit_scenario_evaluator"].data["service_credit_scenario"]
        key_facts.append(c["reason"])
        evidence.append({"kind": "computation", "label": "Service credit (scenario)", "detail": c["reason"]})
    if "ticket_lookup" in results and results["ticket_lookup"].ok:
        t = results["ticket_lookup"].data
        sev = t.get("classified_severity", {})
        key_facts.append(f"Ticket {t['code']}: classified {sev.get('severity')} ({sev.get('label')}).")
        if t.get("known_issues"):
            key_facts.append("Matches known issue(s): " + ", ".join(k["code"] for k in t["known_issues"]) + ".")
    if "known_issue_match" in results and results["known_issue_match"].ok:
        for m in results["known_issue_match"].data.get("matches", []):
            evidence.append({"kind": "document", "label": m["code"], "detail": m["guidance"]})

    # Surface RBAC-blocked / not-found lookups explicitly (no silent fallback).
    for key in ("order_lookup", "ticket_lookup", "cancellation_evaluator", "service_credit_evaluator", "sla_calculator"):
        r = results.get(key)
        if r and not r.ok and r.error == "not_found":
            key_facts.insert(0, r.summary)

    state["evidence"] = evidence
    state["answer"] = {"summary": "", "key_facts": key_facts, "recommendation": ""}

    # Confidence: deterministic computations are high-confidence; retrieval-only
    # answers inherit the retriever's confidence; uncertainty lowers it.
    doc = results.get("document_search")
    retr_conf = doc.data.get("confidence", 0.0) if doc else 0.0
    has_structured = any(
        k in results and results[k].ok
        for k in (
            "sla_calculator", "cancellation_evaluator", "service_credit_evaluator",
            "service_credit_scenario_evaluator", "ticket_lookup", "order_lookup",
        )
    )
    # A scenario-based verdict rests on the caller's self-reported facts (not a
    # verified order), so it's genuinely computed but slightly less certain.
    conf = max(retr_conf, 0.82) if has_structured else retr_conf
    if "service_credit_scenario_evaluator" in results and results["service_credit_scenario_evaluator"].ok:
        conf = min(conf, 0.75)
    # Explicit "don't-promise-when-uncertain" signals lower confidence.
    for key, field in (
        ("cancellation_evaluator", "cancellation"),
        ("service_credit_evaluator", "service_credit"),
        ("service_credit_scenario_evaluator", "service_credit_scenario"),
    ):
        r = results.get(key)
        if r and r.ok and (r.data.get(field) or {}).get("uncertainty"):
            conf = min(conf, 0.55)
    state["confidence"] = round(min(1.0, conf), 3)
    add_trace(state, "reasoner", "Synthesised findings",
              f"{len(key_facts)} key fact(s); confidence {state['confidence']:.2f} ({Confidence.from_score(state['confidence']).name}).")
    return state


def conflict_resolver(state: AgentState) -> AgentState:
    conflicts = state.get("conflicts", [])
    results = state.get("results", {})
    escalation = None

    # Recommend escalation on a breached P1, or an unresolved uncertainty.
    sla = results.get("sla_calculator")
    if sla and sla.ok:
        s = sla.data["sla"]
        if s["breached"] and s["severity"] == "P1":
            escalation = {
                "recommended": True,
                "severity": "P1",
                "reason": f"P1 first-response SLA is breached ({s['target_human']} target, elapsed {s['elapsed_human']}).",
            }
    if conflicts:
        add_trace(state, "conflict_resolver", f"{len(conflicts)} conflict(s) resolved by authority",
                  "; ".join(c["topic"] for c in conflicts))
    else:
        add_trace(state, "conflict_resolver", "No source conflicts", "All evidence agrees or a single authority governs.")
    state["escalation"] = escalation
    return state


def action_validator(state: AgentState) -> AgentState:
    ctx = state["ctx"]
    # (a) commit a pre-approved action this turn.
    if state.get("confirm_action"):
        action = state["confirm_action"]
        tool = registry.get_tool(action.get("tool", ""))
        if tool is None:
            state["error"] = "Unknown action to confirm."
            return state
        try:
            result = tool.commit(ctx, action)
            _collect(state, result)
            state["committed"] = {"ok": result.ok, "summary": result.summary, "data": result.data}
            add_trace(state, "action_executor", "Action executed", result.summary)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Commit failed")
            state["error"] = "The action could not be completed."
        return state

    # (b) prepare (never execute) any planned state-changing action.
    _run_phase(state, "action")
    for call in state.get("plan", []):
        if call["phase"] != "action":
            continue
        res = state.get("results", {}).get(call["tool"])
        if res and res.requires_confirmation:
            state["pending_action"] = res.proposed_action
            add_trace(state, "action_validator", "Action prepared (awaiting confirmation)", res.summary)
    return state


def confirmation(state: AgentState) -> AgentState:
    if state.get("pending_action"):
        add_trace(state, "confirmation", "Confirmation required",
                  "The action will run only after explicit user approval.")
    return state


def response_generator(state: AgentState) -> AgentState:
    state["citations"] = _dedupe_citations(state.get("citations", []))
    answer = state.get("answer", {}) or {}

    if state.get("committed"):
        answer["summary"] = state["committed"]["summary"]
        answer["recommendation"] = "Action completed."
    elif state.get("error"):
        answer["summary"] = state["error"]
    elif state["intent"].get("type") == "greeting":
        answer["summary"] = "Hello! I'm the ParcelPilot support assistant. Ask me about orders, tickets, SLAs, cancellations, or service credits."
    else:
        primary = answer.get("key_facts", [])
        answer["summary"] = primary[0] if primary else "Here's what I found based on the available evidence."
        if state.get("escalation", {}) and state["escalation"].get("recommended"):
            answer["recommendation"] = "Escalation recommended: " + state["escalation"]["reason"]

    answer["confidence"] = state.get("confidence", 0.0)
    answer["confidence_band"] = Confidence.from_score(state.get("confidence", 0.0)).name
    answer["pending_action"] = state.get("pending_action")
    answer["escalation"] = state.get("escalation")
    state["answer"] = answer
    add_trace(state, "response_generator", "Response composed",
              f"{len(state['citations'])} source(s), {len(state.get('conflicts', []))} conflict(s).")
    return state


def audit_logger(state: AgentState) -> AgentState:
    ctx = state["ctx"]
    try:
        ctx.audit().record(
            action="agent_turn",
            resource_type="conversation",
            resource_id=str(ctx.conversation_id) if ctx.conversation_id else None,
            success=not state.get("error"),
            details={
                "intent": state.get("intent", {}).get("type"),
                "tools": [t["tool"] for t in state.get("tool_calls", [])],
                "confidence": state.get("confidence"),
                "conflicts": len(state.get("conflicts", [])),
                "pending_action": bool(state.get("pending_action")),
                "committed": bool(state.get("committed")),
            },
            request_id=ctx.request_id,
        )
    except Exception:  # audit must not break the turn
        logger.warning("Audit logging failed", exc_info=True)
    add_trace(state, "audit_logger", "Audit recorded", "Decision, tools, and outcome logged.")
    return state
