"""The agent layer — a LangGraph state machine orchestrating the support brain.

Graph nodes (each single-responsibility):
    intent → authorization → planner → retriever → structured_data → reasoner →
    conflict_resolver → action_validator → confirmation → response_generator →
    audit_logger

The graph gathers evidence with RBAC-scoped tools, resolves source conflicts by
authority, prepares (never auto-executes) state-changing actions, and emits a
fully-explained structured answer. A separate Narrator turns that structured
answer into streamed prose — the LLM phrases, it never invents facts.
"""
