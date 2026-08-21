"""Machine-readable business rules distilled from the policy documents.

These constants are the structured twin of the human-readable knowledge base.
Services (SLA, cancellation, service-credit) read these; agreements copy their
overrides into ``Agreement.terms`` at seed time so a single account's rules are
self-contained.

SLA targets are normalised to ``{"minutes": int, "mode": "calendar"|"business"}``.
    * ``calendar`` = wall-clock (24x7 coverage).
    * ``business``  = counted only during Mon–Fri 09:00–18:00 IST (see clock.py).
Wording interpretation (documented): a cell that says "24x7" or a bare hour
count on the Enterprise row is treated as ``calendar``; anything qualified with
"business" is ``business``. "1 business day" = one 9-hour working day.
"""

from __future__ import annotations

from app.core.clock import BUSINESS_MINUTES_PER_DAY

_BDAY = BUSINESS_MINUTES_PER_DAY  # 540 minutes


def _cal(minutes: int) -> dict:
    return {"minutes": minutes, "mode": "calendar"}


def _biz(minutes: int) -> dict:
    return {"minutes": minutes, "mode": "business"}


# --- Default first-response SLA targets (Support Policy v3, §3) ------------
POLICY_SLA_DEFAULTS: dict[str, dict[str, dict]] = {
    "enterprise": {"P1": _cal(30), "P2": _cal(120), "P3": _biz(1 * _BDAY)},
    "growth": {"P1": _biz(120), "P2": _biz(240), "P3": _biz(2 * _BDAY)},
    "standard": {"P1": _biz(240), "P2": _biz(1 * _BDAY), "P3": _biz(2 * _BDAY)},
}

# --- Deprecated v2 targets (retained only to explain conflicts) ------------
DEPRECATED_SLA_V2: dict[str, dict[str, dict]] = {
    "enterprise": {"P1": _cal(60), "P2": _cal(240), "P3": _biz(2 * _BDAY)},
    "growth": {"P1": _biz(240), "P2": _biz(1 * _BDAY), "P3": _biz(3 * _BDAY)},
    "standard": {"P1": _biz(480), "P2": _biz(2 * _BDAY), "P3": _biz(3 * _BDAY)},
}

# --- Cancellation & Service Credit SOP v4 defaults -------------------------
SOP_DEFAULTS: dict = {
    "cancellation": {
        "free_window_minutes": 30,      # no fee within 30 min of booking
        "fee_inr": 250,                 # after 30 min, for BOOKED not-yet-picked-up
    },
    "service_credit": {
        "delay_threshold_minutes": 120,  # >2h past pickup window end
        "amount_inr": 500,               # default credit is lower of 500 or 10% fee
        "percent_of_fee": 0.10,
        "manager_approval_above_inr": 1000,
    },
}

# --- Per-account agreement overrides (copied into Agreement.terms) ---------
AGREEMENT_TERMS: dict[str, dict] = {
    "ACCT-001": {  # Northstar Logistics — Enterprise
        "sla": {"P1": _cal(15), "P2": _cal(60), "P3": _biz(8 * 60)},
        "coverage": "24x7",
        "weekend_support": True,
        "cancellation": {"fee_waived": True},
        "service_credit": {"monthly_cap_inr": 5000, "use_sop": True},
    },
    "ACCT-002": {  # LumenWorks — Growth
        "sla": {"P1": _biz(120), "P2": _biz(240), "P3": _biz(2 * _BDAY)},
        "coverage": "business",
        "weekend_support": False,
        "cancellation": {"fee_waived": False},
        "service_credit": {
            "delay_threshold_minutes": 240,  # >4h past window
            "amount_inr": 300,
            "type": "fixed",
            "replaces_sop": True,
        },
    },
}
