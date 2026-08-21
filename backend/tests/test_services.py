"""Business-rule services — the deterministic brain, tested against real data."""

import pytest

from app.repositories.logistics_repo import AgreementRepository, OrderRepository, TicketRepository
from app.repositories.organization_repo import AccountRepository
from app.services.cancellation_service import evaluate_cancellation
from app.services.service_credit_service import (
    evaluate_service_credit,
    evaluate_service_credit_scenario,
)
from app.services.severity_service import classify_severity
from app.services.sla_service import compute_sla


@pytest.fixture()
def admin(principal_factory):
    return principal_factory("admin@parcelpilot.com")


def _account(session, admin, code):
    return AccountRepository(session, admin).get_by_code(code)


def _agreement(session, admin, account):
    return AgreementRepository(session, admin).get_current_for_account(account.id)


@pytest.mark.parametrize(
    "subject,desc,expected",
    [
        ("All shipment creation is failing", "Every user gets HTTP 500 creating any shipment.", "P1"),
        ("Bulk upload fails for 4,200-row CSV", "Reaches 70% then fails. One-by-one still works.", "P2"),
        ("How do we change the billing contact?", "Replace billing-contact email.", "P3"),
        ("Possible API key exposure", "Employee posted a screenshot with a production API key.", "P1"),
    ],
)
def test_severity_classification(subject, desc, expected):
    assert classify_severity(subject, desc).severity == expected


def test_northstar_p1_sla_agreement_wins_and_breached(session, admin):
    ticket = TicketRepository(session, admin).get_by_code("TKT-501")
    account = _account(session, admin, "ACCT-001")
    agreement = _agreement(session, admin, account)
    sla = compute_sla(account, agreement, "P1", ticket.business_created_at)
    assert sla.target_minutes == 15
    assert sla.source == "customer_agreement"
    assert sla.breached is True
    assert any(c.topic.startswith("P1") for c in sla.conflicts)


def test_axis_p1_sla_falls_back_to_policy(session, admin):
    ticket = TicketRepository(session, admin).get_by_code("TKT-505")
    account = _account(session, admin, "ACCT-004")  # no agreement
    agreement = _agreement(session, admin, account)
    sla = compute_sla(account, agreement, "P1", ticket.business_created_at)
    assert sla.target_minutes == 30
    assert sla.source == "support_policy_v3"
    assert sla.breached is True


def test_northstar_cancellation_fee_waived_with_conflict(session, admin):
    order = OrderRepository(session, admin).get_by_code("ORD-1001")
    account = _account(session, admin, "ACCT-001")
    result = evaluate_cancellation(order, account, _agreement(session, admin, account))
    assert result.allowed is True
    assert result.fee_inr == 0.0
    assert result.fee_waived is True
    assert result.conflicts  # agreement vs SOP vs historical ticket


def test_lumenworks_cancellation_charges_fee(session, admin):
    order = OrderRepository(session, admin).get_by_code("ORD-2001")
    account = _account(session, admin, "ACCT-002")
    result = evaluate_cancellation(order, account, _agreement(session, admin, account))
    assert result.allowed is True
    assert result.fee_inr == 250.0


def test_picked_up_order_cannot_cancel(session, admin):
    order = OrderRepository(session, admin).get_by_code("ORD-1002")
    account = _account(session, admin, "ACCT-001")
    result = evaluate_cancellation(order, account, _agreement(session, admin, account))
    assert result.allowed is False
    assert result.recommended_action == "return_to_origin"


def test_lumenworks_service_credit_agreement_override(session, admin):
    order = OrderRepository(session, admin).get_by_code("ORD-2002")
    account = _account(session, admin, "ACCT-002")
    result = evaluate_service_credit(order, account, _agreement(session, admin, account))
    assert result.eligible is True
    assert result.amount_inr == 300.0
    assert result.basis == "agreement"
    assert result.requires_manager_approval is False


def test_service_credit_refused_when_no_carrier_fault(session, admin):
    order = OrderRepository(session, admin).get_by_code("ORD-4001")  # delivered, no fault
    account = _account(session, admin, "ACCT-004")
    result = evaluate_service_credit(order, account, _agreement(session, admin, account))
    assert result.eligible is False


# --- Hypothetical scenario reasoning (no order code — from the brief's own
# example: "A pickup is three hours late because of carrier fault. Should I
# get a service credit?") ------------------------------------------------

def test_scenario_lumenworks_below_their_agreement_threshold(session, admin):
    account = _account(session, admin, "ACCT-002")  # LumenWorks: >4h fixed INR 300
    result = evaluate_service_credit_scenario(
        account, _agreement(session, admin, account),
        delay_hours=3, carrier_fault=True, customer_fault=False,
    )
    assert result.eligible is False  # 3h does not exceed their 4h threshold


def test_scenario_lumenworks_above_their_agreement_threshold(session, admin):
    account = _account(session, admin, "ACCT-002")
    result = evaluate_service_credit_scenario(
        account, _agreement(session, admin, account),
        delay_hours=5, carrier_fault=True, customer_fault=False,
    )
    assert result.eligible is True
    assert result.amount_inr == 300.0
    assert result.basis == "agreement"


def test_scenario_falls_back_to_sop_default_with_no_agreement(session, admin):
    account = _account(session, admin, "ACCT-003")  # Beacon: no custom agreement
    result = evaluate_service_credit_scenario(
        account, _agreement(session, admin, account),
        delay_hours=3, carrier_fault=True, customer_fault=False,
    )
    assert result.eligible is True  # 3h exceeds the SOP default 2h threshold
    assert result.basis == "sop_default"
    assert result.amount_inr == 0.0  # exact amount needs a real order's fee


def test_scenario_customer_fault_is_refused(session, admin):
    account = _account(session, admin, "ACCT-002")
    result = evaluate_service_credit_scenario(
        account, _agreement(session, admin, account),
        delay_hours=5, carrier_fault=False, customer_fault=True,
    )
    assert result.eligible is False
