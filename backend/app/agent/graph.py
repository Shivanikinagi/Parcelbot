"""Compile and run the LangGraph agent.

The graph is linear across eleven single-responsibility nodes; branching
behaviour (confirm-and-commit vs full pipeline, action vs informational) is
handled inside the nodes so the topology stays readable. The graph is compiled
once and reused.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.agent import nodes
from app.agent.state import AgentState, new_state
from app.tools.base import ToolContext

# Node names must not collide with AgentState keys (LangGraph constraint),
# so nodes use verb names while their conceptual roles match the docs.
_NODE_SEQUENCE = [
    ("classify_intent", nodes.intent_classification),
    ("authorize", nodes.authorization),
    ("build_plan", nodes.planner),
    ("retrieve", nodes.retriever),
    ("query_structured", nodes.structured_data),
    ("reason", nodes.reasoner),
    ("resolve_conflicts", nodes.conflict_resolver),
    ("validate_action", nodes.action_validator),
    ("request_confirmation", nodes.confirmation),
    ("generate_response", nodes.response_generator),
    ("write_audit", nodes.audit_logger),
]


@lru_cache(maxsize=1)
def get_graph():
    graph = StateGraph(AgentState)
    for name, fn in _NODE_SEQUENCE:
        graph.add_node(name, fn)
    graph.set_entry_point(_NODE_SEQUENCE[0][0])
    for (name, _), (nxt, _) in zip(_NODE_SEQUENCE, _NODE_SEQUENCE[1:]):
        graph.add_edge(name, nxt)
    graph.add_edge(_NODE_SEQUENCE[-1][0], END)
    return graph.compile()


def run_agent(
    ctx: ToolContext,
    query: str,
    confirm_action: dict | None = None,
    history: list[dict] | None = None,
) -> AgentState:
    """Invoke the agent graph and return the final state.

    ``history`` is the recent prior turns of this conversation (oldest first,
    each ``{"role": ..., "content": ...}``) — used to carry forward entities
    for natural follow-ups ("why did you choose that SLA?") and to give the
    LLM narrator short-term conversational context.
    """
    state = new_state(query, ctx, confirm_action, history)
    # recursion_limit comfortably above our fixed node count.
    final = get_graph().invoke(state, {"recursion_limit": 50})
    return final  # type: ignore[return-value]
