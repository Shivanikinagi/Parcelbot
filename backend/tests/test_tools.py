"""Tool layer: validation, RBAC, telemetry, and two-phase state changes."""

from app.tools import registry


def test_registry_has_expected_tools():
    names = {t.name for t in registry.all_tools()}
    for expected in ["document_search", "order_lookup", "ticket_lookup", "sla_calculator",
                     "cancellation_evaluator", "service_credit_evaluator", "escalation_creator",
                     "follow_up_task_creator", "ticket_update", "customer_history"]:
        assert expected in names
    assert len(names) >= 12


def test_order_lookup_rbac(ctx_factory):
    ctx = ctx_factory("ravi@lumenworks.example")
    res = registry.get_tool("order_lookup").execute(ctx, {"order_code": "ORD-1001"})
    assert res.ok is False
    assert res.error == "not_found"


def test_invalid_arguments_are_contained(ctx_factory):
    ctx = ctx_factory("admin@parcelpilot.com")
    res = registry.get_tool("sla_calculator").execute(ctx, {})  # neither ticket nor account+sev
    assert res.ok is False  # validation failure, no exception leaks


def test_document_search_returns_citations(ctx_factory):
    ctx = ctx_factory("admin@parcelpilot.com")
    res = registry.get_tool("document_search").execute(ctx, {"query": "cancellation fee window"})
    assert res.ok is True
    assert res.citations


def test_escalation_two_phase(ctx_factory, session):
    ctx = ctx_factory("maya@parcelpilot.com")
    tool = registry.get_tool("escalation_creator")
    prep = tool.execute(ctx, {"ticket_code": "TKT-501"})
    assert prep.requires_confirmation is True
    assert prep.proposed_action["params"]["severity"] == "P1"
    # Nothing created yet.
    from app.models.workflow import Escalation
    before = session.query(Escalation).count()
    committed = tool.commit(ctx, prep.proposed_action)
    assert committed.ok is True
    assert session.query(Escalation).count() == before + 1


def test_customer_cannot_use_ticket_update(ctx_factory):
    ctx = ctx_factory("ravi@lumenworks.example")
    res = registry.get_tool("ticket_update").execute(ctx, {"ticket_code": "TKT-2001", "status": "closed"})
    assert res.ok is False  # lacks update_ticket permission
