"""Order-cancellation eligibility per SOP v4 §1 and agreement overrides.

Handles the status lifecycle (DRAFT/BOOKED/PICKED_UP/DELIVERED), the 30-minute
free window, the ₹250 default fee, and per-account fee waivers. Where the
agreement waives a fee that the default SOP — and a wrong historical ticket —
would charge, the disagreement is surfaced as an explicit, authority-ranked
conflict rather than silently resolved.
"""

from __future__ import annotations

from app.core.clock import ensure_ist, reference_now
from app.db.policy_data import SOP_DEFAULTS
from app.models.logistics import Agreement, Order
from app.models.organization import Account
from app.schemas.results import CancellationResult, Citation, Conflict, ConflictSource

_SOP_CITATION = Citation(
    document_code="SOP-CANCEL-CREDIT-V4",
    title="ParcelPilot Cancellation & Service Credit SOP v4",
    heading="§1 Order cancellation",
    source_type="sop",
    status="current",
    authority_rank=3,
    source_file="03_Cancellation_and_Service_Credit_SOP_v4.pdf",
)


def evaluate_cancellation(
    order: Order, account: Account, agreement: Agreement | None
) -> CancellationResult:
    status = order.status.upper()
    citations = [_SOP_CITATION]

    if status == "DRAFT":
        return CancellationResult(
            allowed=True,
            order_status=status,
            fee_inr=0.0,
            reason="DRAFT shipments may be cancelled with no fee (SOP §1).",
            recommended_action="cancel_order",
            citations=citations,
        )
    if status == "DELIVERED":
        return CancellationResult(
            allowed=False,
            order_status=status,
            reason="Delivered shipments cannot be cancelled (SOP §1).",
            citations=citations,
        )
    if status == "PICKED_UP":
        return CancellationResult(
            allowed=False,
            order_status=status,
            reason=(
                "The shipment has been picked up and cannot be cancelled. Use the "
                "return-to-origin workflow if the customer wants the parcel returned (SOP §1)."
            ),
            recommended_action="return_to_origin",
            citations=citations,
        )

    # --- BOOKED, not yet picked up --------------------------------------
    ref_point = order.cancellation_requested_at or reference_now()
    minutes_since = None
    if order.booked_at is not None:
        minutes_since = max(0, int((ensure_ist(ref_point) - ensure_ist(order.booked_at)).total_seconds() // 60))

    cancel_terms = (agreement.terms.get("cancellation", {}) if agreement and isinstance(agreement.terms, dict) else {})
    fee_waived = bool(cancel_terms.get("fee_waived"))

    conflicts: list[Conflict] = []
    free_window = SOP_DEFAULTS["cancellation"]["free_window_minutes"]
    default_fee = SOP_DEFAULTS["cancellation"]["fee_inr"]

    if fee_waived:
        fee = 0.0
        reason = (
            f"{account.name}'s agreement waives the cancellation fee for any BOOKED shipment "
            "before pickup, regardless of elapsed time (agreement §2). No fee applies."
        )
        citations.insert(
            0,
            Citation(
                document_code=agreement.code,
                title=agreement.title,
                heading="§2 Shipment cancellation",
                source_type="customer_agreement",
                status="current",
                authority_rank=1,
                source_file=agreement.source_file,
            ),
        )
        # Conflict: default SOP (and a wrong historical ticket) would charge ₹250.
        if minutes_since is not None and minutes_since > free_window:
            conflicts.append(
                Conflict(
                    topic="Cancellation fee",
                    description=(
                        f"The booking was {minutes_since} minutes ago (past the {free_window}-minute "
                        "free window), so the default SOP and a past ticket would charge a fee — but "
                        "the signed agreement waives it."
                    ),
                    sources=[
                        ConflictSource(label=f"{account.name} agreement §2", value="No fee (waived)", authority_rank=1),
                        ConflictSource(label="SOP v4 §1", value=f"INR {default_fee} after {free_window} min", authority_rank=3),
                        ConflictSource(label="Historical ticket TKT-450", value=f"INR {default_fee} charged", authority_rank=6, status="historical"),
                    ],
                    resolution="The signed customer agreement takes precedence (Support Policy §1). Historical tickets are context only. No fee is charged.",
                    resolved_value="No cancellation fee",
                )
            )
    else:
        if minutes_since is not None and minutes_since <= free_window:
            fee = 0.0
            reason = f"Cancellation requested {minutes_since} min after booking — within the {free_window}-minute free window, so no fee (SOP §1)."
        else:
            fee = float(default_fee)
            reason = (
                f"Cancellation requested {minutes_since} min after booking — past the "
                f"{free_window}-minute free window, so a INR {default_fee} fee applies (SOP §1). "
                "No agreement waiver is on file for this account."
            )

    return CancellationResult(
        allowed=True,
        order_status=status,
        fee_inr=fee,
        fee_waived=fee_waived,
        reason=reason,
        minutes_since_booking=minutes_since,
        recommended_action="cancel_order",
        conflicts=conflicts,
        citations=citations,
    )
