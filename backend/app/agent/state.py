"""Agent graph state and small value types.

The state is a plain dict (LangGraph ``TypedDict``) carrying both the working
data and non-serialised runtime handles (the ToolContext). We run the graph
in-process without a checkpointer, so holding live objects in state is safe and
avoids threading a separate config through every node.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.tools.base import ToolContext


class PlannedCall(TypedDict):
    tool: str
    args: dict[str, Any]
    phase: str  # "retrieve" | "structured" | "action"
    why: str


class TraceEvent(TypedDict):
    node: str
    label: str
    detail: str


class AgentState(TypedDict, total=False):
    # --- inputs ----------------------------------------------------------
    query: str
    ctx: ToolContext            # runtime handle (session + principal + ids)
    confirm_action: dict | None  # a pre-approved action to commit this turn

    # --- derived ---------------------------------------------------------
    intent: dict
    entities: dict
    plan: list[PlannedCall]
    tool_calls: list[dict]      # timeline of executed tools
    results: dict               # tool_name -> ToolResult (live objects, in-process)
    evidence: list[dict]        # structured findings
    citations: list[dict]
    conflicts: list[dict]
    confidence: float
    pending_action: dict | None
    escalation: dict | None
    answer: dict                # structured AnswerDraft
    trace: list[TraceEvent]     # reasoning timeline (high level)
    committed: dict | None      # result of committing confirm_action
    error: str | None


def new_state(query: str, ctx: ToolContext, confirm_action: dict | None = None) -> AgentState:
    return AgentState(
        query=query,
        ctx=ctx,
        confirm_action=confirm_action,
        intent={},
        entities={},
        plan=[],
        tool_calls=[],
        results={},
        evidence=[],
        citations=[],
        conflicts=[],
        confidence=0.0,
        pending_action=None,
        escalation=None,
        answer={},
        trace=[],
        committed=None,
        error=None,
    )


def add_trace(state: AgentState, node: str, label: str, detail: str = "") -> None:
    state.setdefault("trace", []).append(TraceEvent(node=node, label=label, detail=detail))
