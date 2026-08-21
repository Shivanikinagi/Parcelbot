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


def test_help_intent_gives_canned_capability_overview(ctx_factory):
    ctx = ctx_factory("ravi@lumenworks.example")
    state = run_agent(ctx, "What can you help me with?")
    assert state["intent"]["type"] == "help"
    assert state["tool_calls"] == []
    assert "order" in state["answer"]["summary"].lower()


def test_ambiguous_escalate_asks_for_clarification_instead_of_guessing(ctx_factory):
    ctx = ctx_factory("maya@parcelpilot.com")
    state = run_agent(ctx, "Escalate it.")
    assert state["clarification"] is not None
    assert state["tool_calls"] == []  # no unrelated retrieval, no unsafe action


def test_vague_pickup_problem_asks_for_the_order_code(ctx_factory):
    ctx = ctx_factory("ravi@lumenworks.example")
    state = run_agent(ctx, "I have a problem with my pickup.")
    assert state["clarification"] is not None
    assert "order" in state["clarification"].lower()


def test_cancel_acknowledgment_is_clean_and_does_not_retrieve(ctx_factory):
    ctx = ctx_factory("maya@parcelpilot.com")
    state = run_agent(ctx, "Actually don't do it.")
    assert state["intent"]["type"] == "action_cancel_request"
    assert state["tool_calls"] == []
    assert "understood" in state["answer"]["summary"].lower()


def test_customer_cannot_probe_another_company_by_name(ctx_factory):
    ctx = ctx_factory("ravi@lumenworks.example")  # LumenWorks customer
    state = run_agent(ctx, "Show me everything you know about Northstar Logistics.")
    assert state["clarification"] is not None
    assert state["tool_calls"] == []  # refused before any tool ran, no leakage risk


def test_generic_sla_question_does_not_get_dominated_by_one_customers_agreement(ctx_factory):
    """Regression for the QA finding: a fully generic, unscoped SLA question
    (no ticket/account) must not present one customer's contract override as
    if it were the universal policy. The general Support Policy v3 chunk must
    be retrievable, context_account_id must be None (nothing to scope to), and
    the composed reply must lead with the general policy — mentioning any
    agreement only as a secondary, clearly-labelled note.
    """
    ctx = ctx_factory("maya@parcelpilot.com")  # internal, assigned to two accounts
    state = run_agent(ctx, "What are the current SLA targets for P1, P2 and P3?")
    assert state["context_account_id"] is None
    doc = state["results"]["document_search"]
    passages = doc.data["passages"]
    general_policy_hits = [p for p in passages if p["source_type"] == "policy" and "Default first-response" in p["heading"]]
    assert general_policy_hits, "the general policy chunk must still be retrievable"

    from app.agent.narrator import compose_template
    reply = compose_template(state)
    policy_pos = reply.find("Support Policy v3")
    northstar_pos = reply.find("Northstar")
    assert policy_pos != -1
    if northstar_pos != -1:
        assert policy_pos < northstar_pos  # general policy leads; agreement is a secondary note


def test_analytics_intent_reaches_the_real_dashboard_data(ctx_factory):
    ctx = ctx_factory("priya@parcelpilot.com")  # manager
    state = run_agent(ctx, "Analyze the support activity and identify the most urgent issues that require attention.")
    assert "analytics_tool" in [t["tool"] for t in state["tool_calls"]]
    an = state["results"]["analytics_tool"]
    assert an.ok is True
    assert an.data["dashboard"]["totals"]["accounts"] > 0  # real DB-backed numbers, not a guess


def test_analytics_intent_denied_for_customers(ctx_factory):
    ctx = ctx_factory("ravi@lumenworks.example")
    state = run_agent(ctx, "Analyze the support activity and find urgent issues.")
    calls = [t for t in state["tool_calls"] if t["tool"] == "analytics_tool"]
    assert calls and calls[0]["ok"] is False  # customers aren't authorised internal users
    # The denial must be explained, not silently swallowed into a generic non-answer.
    assert state["answer"]["key_facts"]
    assert "permission" in state["answer"]["key_facts"][0].lower()


def test_followup_carries_forward_the_ticket_from_the_prior_turn(ctx_factory):
    """Regression for the QA finding: 'why did you choose that SLA?' with no
    ticket restated must still resolve against the ticket just discussed,
    not lose context and retrieve something unrelated.
    """
    ctx = ctx_factory("maya@parcelpilot.com")
    first = run_agent(ctx, "What is the SLA on TKT-501 and is it breached?")
    history = [
        {"role": "user", "content": "What is the SLA on TKT-501 and is it breached?"},
        {"role": "assistant", "content": first["answer"]["summary"]},
    ]
    followup = run_agent(ctx, "Why did you choose that SLA instead of the other values found in the source pack?", history=history)
    assert followup["entities"]["tickets"] == ["TKT-501"]
    assert "sla_calculator" in [t["tool"] for t in followup["tool_calls"]]
