"""Typed results shared by services, tools, and the API.

Keeping these as Pydantic models (not loose dicts) means every business
computation has a validated, self-documenting shape — the same object flows
from a service, through a tool, into the agent's evidence bundle, and out to the
UI without re-parsing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    marker: str = ""
    document_code: str = ""
    title: str = ""
    heading: str = ""
    source_type: str = ""
    status: str = "current"
    authority_rank: int = 5
    source_file: str | None = None
    relevance: float = 0.0


class ConflictSource(BaseModel):
    label: str
    value: str
    authority_rank: int
    status: str = "current"


class Conflict(BaseModel):
    """A detected disagreement between sources, resolved by authority."""

    topic: str
    description: str
    sources: list[ConflictSource] = Field(default_factory=list)
    resolution: str
    resolved_value: str | None = None
    recommended_action: str | None = None
    requires_escalation: bool = False


class SeverityResult(BaseModel):
    severity: Literal["P1", "P2", "P3"]
    label: str
    rationale: str
    signals: list[str] = Field(default_factory=list)
    confidence: float = 0.7


class SLAResult(BaseModel):
    severity: str
    plan: str
    target_minutes: int
    mode: str  # calendar | business
    coverage: str  # 24x7 | business
    source: str  # "customer_agreement" | "support_policy_v3"
    due_at: datetime | None = None
    elapsed_minutes: int = 0
    remaining_minutes: int = 0
    breached: bool = False
    target_human: str = ""
    elapsed_human: str = ""
    explanation: str = ""
    conflicts: list[Conflict] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class CancellationResult(BaseModel):
    allowed: bool
    order_status: str
    fee_inr: float = 0.0
    fee_waived: bool = False
    reason: str = ""
    minutes_since_booking: int | None = None
    recommended_action: str | None = None  # e.g. "cancel_order" | "return_to_origin"
    uncertainty: str | None = None
    conflicts: list[Conflict] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class ServiceCreditResult(BaseModel):
    eligible: bool
    amount_inr: float = 0.0
    basis: str = ""  # "agreement" | "sop_default"
    reason: str = ""
    minutes_past_window: int | None = None
    requires_manager_approval: bool = False
    monthly_cap_inr: float | None = None
    uncertainty: str | None = None
    conflicts: list[Conflict] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    """One unit of evidence in the agent's bundle (retrieved or computed)."""

    kind: Literal["document", "structured", "computation"]
    label: str
    detail: str
    source_type: str = ""
    authority_rank: int = 5
    status: str = "current"
    data: dict[str, Any] = Field(default_factory=dict)
