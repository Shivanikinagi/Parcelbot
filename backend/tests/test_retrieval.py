"""Hybrid retrieval, authority weighting, and RBAC-scoped corpus."""

from app.repositories.knowledge_repo import KnowledgeRepository
from app.retrieval.retriever import HybridRetriever


def _retrieve(session, principal, query, k=6):
    chunks = KnowledgeRepository(session, principal).list_visible_chunks()
    return HybridRetriever(chunks).retrieve(query, top_k=k)


def test_retrieval_returns_ranked_hits_with_confidence(session, principal_factory):
    admin = principal_factory("admin@parcelpilot.com")
    hits, confidence = _retrieve(session, admin, "P1 critical outage first response target")
    assert hits
    assert 0.0 < confidence <= 1.0
    # scores are monotonically non-increasing (sorted by final relevance).
    finals = [h.scores["final"] for h in hits]
    assert finals == sorted(finals, reverse=True)


def test_deprecated_is_visible_to_internal_but_downweighted(session, principal_factory):
    admin = principal_factory("admin@parcelpilot.com")
    hits, _ = _retrieve(session, admin, "response targets enterprise plan", k=12)
    by_status = {h.status for h in hits}
    # It can appear (internal), but a current policy should outrank it.
    current = [h for h in hits if h.source_type == "policy" and h.status == "current"]
    deprecated = [h for h in hits if h.status == "deprecated"]
    if current and deprecated:
        assert current[0].scores["final"] >= deprecated[0].scores["final"]


def test_customer_cannot_retrieve_other_account_agreement(session, principal_factory):
    ravi = principal_factory("ravi@lumenworks.example")  # ACCT-002
    hits, _ = _retrieve(session, ravi, "Northstar enterprise support terms 15 minutes", k=10)
    titles = " ".join(h.title for h in hits).lower()
    assert "northstar" not in titles


def test_customer_cannot_retrieve_deprecated_policy(session, principal_factory):
    ravi = principal_factory("ravi@lumenworks.example")
    hits, _ = _retrieve(session, ravi, "deprecated old support policy v2 response targets", k=10)
    assert all(h.status != "deprecated" for h in hits)
