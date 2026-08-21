"""SLA computation with full source-precedence handling.

Resolves the first-response target for a ticket by walking the authority chain:
    signed customer agreement  →  current Support Policy v3  →  (deprecated v2)
The deprecated value is computed too, purely so the agent can *show* the
conflict and explain why it was ignored. Breach is evaluated against the fixed
dataset snapshot, honouring 24x7 vs business-hours coverage.
"""

from __future__ import annotations

from datetime import datetime

from app.core.clock import (
    add_business_minutes,
    business_minutes_between,
    ensure_ist,
    format_duration,
    reference_now,
)
from app.db.policy_data import DEPRECATED_SLA_V2, POLICY_SLA_DEFAULTS
from app.models.logistics import Agreement
from app.models.organization import Account
from app.schemas.results import Citation, Conflict, ConflictSource, SLAResult

_SEV_LABEL = {"P1": "Critical", "P2": "High", "P3": "Normal"}


def _human_target(target: dict) -> str:
    minutes, mode = target["minutes"], target["mode"]
    if mode == "calendar":
        return f"{format_duration(minutes)} (24x7)"
    if minutes % 540 == 0:
        n = minutes // 540
        return f"{n} business day{'s' if n != 1 else ''}"
    if minutes % 60 == 0:
        return f"{minutes // 60} business hours"
    return f"{format_duration(minutes)} business time"


def _due_at(created_at: datetime, target: dict) -> datetime:
    created_at = ensure_ist(created_at)
    if target["mode"] == "calendar":
        from datetime import timedelta

        return created_at + timedelta(minutes=target["minutes"])
    return add_business_minutes(created_at, target["minutes"])


def _elapsed(created_at: datetime, mode: str) -> int:
    created_at = ensure_ist(created_at)
    now = reference_now()
    if mode == "calendar":
        return max(0, int((now - created_at).total_seconds() // 60))
    return business_minutes_between(created_at, now)


def compute_sla(
    account: Account,
    agreement: Agreement | None,
    severity: str,
    created_at: datetime,
) -> SLAResult:
    plan = account.plan.lower()
    policy_target = POLICY_SLA_DEFAULTS.get(plan, POLICY_SLA_DEFAULTS["standard"])[severity]
    deprecated_target = DEPRECATED_SLA_V2.get(plan, DEPRECATED_SLA_V2["standard"])[severity]

    agreement_target = None
    if agreement and isinstance(agreement.terms, dict):
        agreement_target = agreement.terms.get("sla", {}).get(severity)

    # Authority: agreement first, else current policy.
    if agreement_target:
        target = agreement_target
        source = "customer_agreement"
    else:
        target = policy_target
        source = "support_policy_v3"

    due_at = _due_at(created_at, target)
    elapsed = _elapsed(created_at, target["mode"])
    remaining = target["minutes"] - elapsed
    breached = reference_now() > due_at

    coverage = "24x7" if target["mode"] == "calendar" else "business"

    # --- citations -------------------------------------------------------
    citations: list[Citation] = [
        Citation(
            document_code="POL-SUPPORT-V3",
            title="ParcelPilot Support Policy v3",
            heading="§3 Default first-response targets",
            source_type="policy",
            status="current",
            authority_rank=2,
            source_file="01_Support_Policy_v3_CURRENT.pdf",
        )
    ]
    if source == "customer_agreement" and agreement is not None:
        citations.insert(
            0,
            Citation(
                document_code=agreement.code,
                title=agreement.title,
                heading="§1 Support terms",
                source_type="customer_agreement",
                status="current",
                authority_rank=1,
                source_file=agreement.source_file,
            ),
        )

    # --- conflict / precedence explanation -------------------------------
    conflicts: list[Conflict] = []
    values_differ = agreement_target and agreement_target["minutes"] != policy_target["minutes"]
    deprecated_differs = deprecated_target["minutes"] != policy_target["minutes"]
    if values_differ or deprecated_differs:
        sources = []
        if agreement_target:
            sources.append(
                ConflictSource(
                    label=f"{account.name} agreement",
                    value=_human_target(agreement_target),
                    authority_rank=1,
                )
            )
        sources.append(
            ConflictSource(
                label="Support Policy v3 (current)",
                value=_human_target(policy_target),
                authority_rank=2,
            )
        )
        sources.append(
            ConflictSource(
                label="Support Policy v2 (deprecated)",
                value=_human_target(deprecated_target),
                authority_rank=7,
                status="deprecated",
            )
        )
        conflicts.append(
            Conflict(
                topic=f"{severity} first-response target",
                description=(
                    "Multiple sources define a first-response target for this "
                    f"{severity} case; they disagree."
                ),
                sources=sources,
                resolution=(
                    "Per Support Policy §1, a signed customer agreement takes precedence "
                    "over the standard policy, and the deprecated v2 policy must not be used."
                    if agreement_target
                    else "The current Support Policy v3 applies; the deprecated v2 policy must not be used."
                ),
                resolved_value=_human_target(target),
                requires_escalation=breached and severity == "P1",
            )
        )

    explanation = (
        f"{severity} ({_SEV_LABEL[severity]}) target is {_human_target(target)}, "
        f"sourced from {'the signed customer agreement' if source == 'customer_agreement' else 'Support Policy v3'}. "
        f"Elapsed since ticket creation: {format_duration(elapsed)}. "
        + ("Target is BREACHED." if breached else f"{format_duration(max(0, remaining))} remaining.")
    )

    return SLAResult(
        severity=severity,
        plan=account.plan,
        target_minutes=target["minutes"],
        mode=target["mode"],
        coverage=coverage,
        source=source,
        due_at=due_at,
        elapsed_minutes=elapsed,
        remaining_minutes=remaining,
        breached=breached,
        target_human=_human_target(target),
        elapsed_human=format_duration(elapsed),
        explanation=explanation,
        conflicts=conflicts,
        citations=citations,
    )
