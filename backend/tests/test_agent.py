"""End-to-end agent graph behaviour."""

from app.agent.graph import run_agent


def test_sla_query_breach_conflict_and_escalation(ctx_factory):
    ctx = ctx_factory("maya@parcelpilot.com")
    state = run_agent(ctx, "What is the SLA on TKT-501 and is it breached?")
    assert state["answer"]["confidence"] >= 0.7
    assert len(state["conflicts"]) >= 1
    assert state["escalation"] and state["escalation"]["recommended"] is True
    assert "sla_calculator" in [t["tool"] for t in state["tool_calls"]]


def test_customer_query_does_not_leak_other_account(ctx_factory):
    ctx = ctx_factory("ravi@lumenworks.example")
    state = run_agent(ctx, "Show me ORD-1001")
    order_calls = [t for t in state["tool_calls"] if t["tool"] == "order_lookup"]
    assert order_calls and order_calls[0]["ok"] is False  # blocked by RBAC


def test_cancellation_conflict_resolution(ctx_factory):
    ctx = ctx_factory("anjali@northstar.example")
    state = run_agent(ctx, "Can I cancel ORD-1001?")
    # Fee is waived by the agreement despite SOP/historical ticket saying otherwise.
    canc = state["results"]["cancellation_evaluator"].data["cancellation"]
    assert canc["fee_inr"] == 0.0
    assert any("fee" in c["topic"].lower() for c in state["conflicts"])


def test_confirm_action_commits(ctx_factory, session):
    ctx = ctx_factory("maya@parcelpilot.com")
    prep = run_agent(ctx, "Escalate TKT-501")
    action = prep["pending_action"]
    assert action is not None
    from app.models.workflow import Escalation
    before = session.query(Escalation).count()
    done = run_agent(ctx, "Confirm", confirm_action=action)
    assert done["committed"]["ok"] is True
    assert session.query(Escalation).count() == before + 1


def test_hypothetical_service_credit_question_from_brief(ctx_factory):
    """The assessment brief's own example: a hypothetical with no order code.

    LumenWorks' agreement requires >4h; a 3h delay must NOT be treated as
    eligible just because it's phrased the same way as the qualifying example.
    """
    ctx = ctx_factory("ravi@lumenworks.example")
    state = run_agent(ctx, "A pickup is three hours late because of carrier fault. Should I get a service credit?")
    assert "service_credit_scenario_evaluator" in [t["tool"] for t in state["tool_calls"]]
    scenario = state["results"]["service_credit_scenario_evaluator"].data["service_credit_scenario"]
    assert scenario["eligible"] is False
    assert "4" in state["answer"]["key_facts"][0]  # cites their 4-hour threshold


def test_greeting_has_no_tool_calls(ctx_factory):
    ctx = ctx_factory("anjali@northstar.example")
    state = run_agent(ctx, "hello there")
    assert state["intent"]["type"] == "greeting"
    assert state["tool_calls"] == []
