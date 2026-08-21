"""Failed-pickup service-credit eligibility per SOP v4 §2/§3 and agreements.

Encodes the guardrails literally: a credit requires carrier fault, no customer
fault, and a delay beyond the (agreement- or SOP-defined) threshold measured
from the end of the pickup window. When any of those facts is unknown the
service refuses to promise a credit and returns an ``uncertainty`` note, exactly
as the SOP demands.
"""

from __future__ import annotations

from app.core.clock import ensure_ist, format_duration, reference_now
from app.db.policy_data import SOP_DEFAULTS
from app.models.logistics import Agreement, Order
from app.models.organization import Account
from app.schemas.results import Citation, Conflict, ConflictSource, ServiceCreditResult

_SOP_CITATION = Citation(
    document_code="SOP-CANCEL-CREDIT-V4",
    title="ParcelPilot Cancellation & Service Credit SOP v4",
    heading="§2 Failed-pickup service credits",
    source_type="sop",
    status="current",
    authority_rank=3,
    source_file="03_Cancellation_and_Service_Credit_SOP_v4.pdf",
)


def evaluate_service_credit(
    order: Order, account: Account, agreement: Agreement | None
) -> ServiceCreditResult:
    citations = [_SOP_CITATION]
    credit_terms = (
        agreement.terms.get("service_credit", {})
        if agreement and isinstance(agreement.terms, dict)
        else {}
    )
    replaces_sop = bool(credit_terms.get("replaces_sop"))

    threshold = (
        credit_terms.get("delay_threshold_minutes")
        if replaces_sop
        else SOP_DEFAULTS["service_credit"]["delay_threshold_minutes"]
    ) or SOP_DEFAULTS["service_credit"]["delay_threshold_minutes"]

    # --- gather facts ----------------------------------------------------
    if order.pickup_window_end is None:
        return ServiceCreditResult(
            eligible=False,
            reason="No scheduled pickup window on record; cannot assess a failed-pickup credit.",
            uncertainty="Missing pickup-window data.",
            citations=citations,
        )

    end = ensure_ist(order.pickup_window_end)
    if order.pickup_actual_at is not None:
        measure_to = ensure_ist(order.pickup_actual_at)
    else:
        measure_to = reference_now()  # still not picked up at snapshot
    minutes_past = max(0, int((measure_to - end).total_seconds() // 60))

    # Uncertainty guardrails (SOP §3: don't promise when facts unknown).
    if not order.carrier_fault:
        return ServiceCreditResult(
            eligible=False,
            minutes_past_window=minutes_past,
            reason=(
                "Carrier fault is not confirmed on this shipment. Per SOP §3, a credit must "
                "not be promised unless carrier fault, timing, and absence of customer fault "
                "are all established."
            ),
            uncertainty="Carrier fault not confirmed.",
            citations=citations,
        )
    if order.customer_fault:
        return ServiceCreditResult(
            eligible=False,
            minutes_past_window=minutes_past,
            reason="A customer-caused issue is recorded, which disqualifies a failed-pickup credit (SOP §2).",
            citations=citations,
        )
    if minutes_past <= threshold:
        return ServiceCreditResult(
            eligible=False,
            minutes_past_window=minutes_past,
            reason=(
                f"Pickup is {format_duration(minutes_past)} past the window end, which does not exceed "
                f"the {format_duration(threshold)} threshold required for a credit."
            ),
            citations=citations,
        )

    # --- eligible: compute amount ---------------------------------------
    conflicts: list[Conflict] = []
    fee = order.shipment_fee_inr or 0.0
    sop_amount = min(
        SOP_DEFAULTS["service_credit"]["amount_inr"],
        SOP_DEFAULTS["service_credit"]["percent_of_fee"] * fee,
    )

    if replaces_sop and credit_terms.get("type") == "fixed":
        amount = float(credit_terms["amount_inr"])
        basis = "agreement"
        citations.insert(
            0,
            Citation(
                document_code=agreement.code,
                title=agreement.title,
                heading="§3 Failed-pickup credits",
                source_type="customer_agreement",
                status="current",
                authority_rank=1,
                source_file=agreement.source_file,
            ),
        )
        conflicts.append(
            Conflict(
                topic="Failed-pickup credit amount & threshold",
                description="The agreement defines a different threshold and amount than the SOP default.",
                sources=[
                    ConflictSource(label=f"{account.name} agreement §3", value=f"INR {amount:.0f} fixed, >{format_duration(threshold)} threshold", authority_rank=1),
                    ConflictSource(label="SOP v4 §2 default", value=f"lower of INR 500 or 10% of fee, >2h threshold", authority_rank=3),
                ],
                resolution="The signed agreement replaces the SOP default for this account (Support Policy §1).",
                resolved_value=f"INR {amount:.0f}",
            )
        )
    else:
        amount = float(sop_amount)
        basis = "sop_default"

    # Monthly cap (e.g. Northstar INR 5,000).
    monthly_cap = credit_terms.get("monthly_cap_inr")
    if monthly_cap is not None and amount > monthly_cap:
        amount = float(monthly_cap)

    requires_approval = amount > SOP_DEFAULTS["service_credit"]["manager_approval_above_inr"]

    return ServiceCreditResult(
        eligible=True,
        amount_inr=amount,
        basis=basis,
        minutes_past_window=minutes_past,
        requires_manager_approval=requires_approval,
        monthly_cap_inr=monthly_cap,
        reason=(
            f"Pickup is {format_duration(minutes_past)} past the window end (> {format_duration(threshold)} threshold), "
            f"carrier is at fault, and no customer fault is recorded. Eligible for a "
            f"INR {amount:.0f} credit ({'agreement §3' if basis == 'agreement' else 'SOP default'})."
            + (" Requires manager approval (> INR 1,000)." if requires_approval else "")
        ),
        conflicts=conflicts,
        citations=citations,
    )
