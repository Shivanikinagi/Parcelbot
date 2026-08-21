"""Conflict detection over retrieved knowledge.

The structured services (SLA, cancellation, credit) already emit precise
conflicts for their domains. This resolver covers the *pure-retrieval* case:
when a query pulls back sources that disagree — e.g. the current policy and its
deprecated predecessor, or an authoritative doc and a stale historical ticket —
it produces an explicit, authority-ranked :class:`Conflict` so the agent can
explain rather than silently pick one.
"""

from __future__ import annotations

from app.retrieval.retriever import ScoredChunk
from app.schemas.results import Conflict, ConflictSource


def detect_source_conflicts(chunks: list[ScoredChunk]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    by_type: dict[str, list[ScoredChunk]] = {}
    for ch in chunks:
        by_type.setdefault(ch.source_type, []).append(ch)

    current_authoritative = [
        c for c in chunks if c.status == "current" and c.source_type in {"policy", "customer_agreement", "sop", "operational_guide"}
    ]

    # 1. Current vs deprecated policy retrieved together.
    if by_type.get("deprecated") and any(c.source_type == "policy" for c in current_authoritative):
        current = next(c for c in current_authoritative if c.source_type == "policy")
        deprecated = by_type["deprecated"][0]
        conflicts.append(
            Conflict(
                topic="Policy version",
                description=(
                    "Both the current policy and a deprecated superseded version were retrieved. "
                    "They may state different targets."
                ),
                sources=[
                    ConflictSource(label=f"{current.title} — {current.heading}", value="current", authority_rank=current.authority_rank),
                    ConflictSource(label=f"{deprecated.title} — {deprecated.heading}", value="deprecated", authority_rank=deprecated.authority_rank, status="deprecated"),
                ],
                resolution="The current policy governs; the deprecated version is retained for reference only and must not be used.",
                resolved_value=current.title,
            )
        )

    # 2. Historical ticket contradicting higher-authority guidance.
    if by_type.get("historical_ticket") and current_authoritative:
        hist = by_type["historical_ticket"][0]
        best = min(current_authoritative, key=lambda c: c.authority_rank)
        conflicts.append(
            Conflict(
                topic="Historical ticket vs current guidance",
                description=(
                    "A past ticket resolution was retrieved alongside authoritative current "
                    "guidance. Historical resolutions are context only and may be incorrect."
                ),
                sources=[
                    ConflictSource(label=f"{best.title} — {best.heading}", value="authoritative", authority_rank=best.authority_rank),
                    ConflictSource(label=hist.title, value="historical (context only)", authority_rank=hist.authority_rank, status="historical"),
                ],
                resolution="Follow the authoritative current source; treat the historical ticket as unverified context.",
                resolved_value=best.title,
            )
        )
    return conflicts
