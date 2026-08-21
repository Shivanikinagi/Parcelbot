"""RBAC enforcement at the repository layer — the security core."""

from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.logistics_repo import OrderRepository, TicketRepository
from app.repositories.organization_repo import AccountRepository


def test_customer_cannot_read_other_accounts_order(session, principal_factory):
    ravi = principal_factory("ravi@lumenworks.example")  # ACCT-002
    repo = OrderRepository(session, ravi)
    assert repo.get_by_code("ORD-1001") is None  # ORD-1001 belongs to ACCT-001
    assert repo.get_by_code("ORD-2001") is not None  # own account


def test_customer_only_sees_own_account(session, principal_factory):
    ravi = principal_factory("ravi@lumenworks.example")
    accounts = AccountRepository(session, ravi).list_accounts()
    assert {a.code for a in accounts} == {"ACCT-002"}


def test_support_scoped_to_assigned_accounts(session, principal_factory):
    maya = principal_factory("maya@parcelpilot.com")  # assigned ACCT-001, ACCT-002
    tickets = TicketRepository(session, maya)
    assert tickets.get_by_code("TKT-501") is not None  # ACCT-001
    assert tickets.get_by_code("TKT-503") is None       # ACCT-003 — not assigned


def test_manager_sees_everything(session, principal_factory):
    priya = principal_factory("priya@parcelpilot.com")
    accounts = AccountRepository(session, priya).list_accounts()
    assert len(accounts) == 4


def test_customer_knowledge_excludes_internal_and_other_agreements(session, principal_factory):
    ravi = principal_factory("ravi@lumenworks.example")
    chunks = KnowledgeRepository(session, ravi).list_visible_chunks()
    sources = {c.source_type for c in chunks}
    # Customers never see deprecated policy, ops guide, or historical tickets.
    assert "deprecated" not in sources
    assert "operational_guide" not in sources
    assert "historical_ticket" not in sources
    # Only their own account's agreement chunks (account_id set) are visible.
    agreement_accounts = {c.account_id for c in chunks if c.source_type == "customer_agreement"}
    assert agreement_accounts == {ravi.account_id}


def test_admin_knowledge_includes_internal(session, principal_factory):
    admin = principal_factory("admin@parcelpilot.com")
    chunks = KnowledgeRepository(session, admin).list_visible_chunks()
    sources = {c.source_type for c in chunks}
    assert {"deprecated", "operational_guide", "historical_ticket", "customer_agreement"} <= sources
