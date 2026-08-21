"""Curated knowledge-base content, transcribed faithfully from the source pack.

Each document is split into section-level chunks (one per ``sections`` entry) so
citations can point at a specific clause ("Support Policy v3 → §3 Default
first-response targets") rather than a whole PDF. Ranking metadata
(``source_type``, ``status``, ``internal_only``, ``account_code``) travels with
every chunk. The seed converts these dicts into Document + DocumentChunk rows
and embeds each chunk.

Provenance: the original PDFs live in ``backend/knowledge/source_pack/``; the
``source_file`` field links each document back to its origin for the UI.
"""

from __future__ import annotations

from app.core.constants import SourceType

# ---------------------------------------------------------------------------
# Each entry: code, title, source_type, status, version, effective_date,
#             account_code (None = global), internal_only, source_file, sections
# ---------------------------------------------------------------------------
KNOWLEDGE_DOCUMENTS: list[dict] = [
    # ----- 01 Support Policy v3 (CURRENT) ---------------------------------
    {
        "code": "POL-SUPPORT-V3",
        "title": "ParcelPilot Support Policy v3",
        "source_type": SourceType.POLICY,
        "status": "current",
        "version": "v3",
        "effective_date": "2026-05-01",
        "account_code": None,
        "internal_only": False,
        "source_file": "01_Support_Policy_v3_CURRENT.pdf",
        "sections": [
            {
                "heading": "§1 Scope and source precedence",
                "content": (
                    "This policy defines default support severity and response targets. "
                    "A signed customer agreement may override these defaults. When sources "
                    "conflict, use the signed customer agreement first, then the current "
                    "support policy, then current product documentation. Historical tickets "
                    "and internal notes are context only and may contain incorrect past guidance."
                ),
            },
            {
                "heading": "§2 Severity definitions",
                "content": (
                    "P1 - Critical: Complete production outage preventing all shipment creation "
                    "for a customer, confirmed security incident or suspected credential exposure, "
                    "or another event causing immediate material business risk with no workaround. "
                    "P2 - High: Major feature unavailable or materially degraded for a customer, but "
                    "core operations remain possible or a workaround exists. "
                    "P3 - Normal: Minor defect, how-to question, configuration request, or issue with "
                    "limited operational impact."
                ),
            },
            {
                "heading": "§3 Default first-response targets",
                "content": (
                    "Default first-response targets by plan (used only when no customer agreement "
                    "overrides them):\n"
                    "Enterprise — P1: 30 minutes, 24x7; P2: 2 hours; P3: 1 business day.\n"
                    "Growth — P1: 2 business hours; P2: 4 business hours; P3: 2 business days.\n"
                    "Standard — P1: 4 business hours; P2: 1 business day; P3: 2 business days."
                ),
            },
            {
                "heading": "§4 Escalation",
                "content": (
                    "P1 incidents should be escalated immediately. If a response target is already "
                    "breached, the agent should clearly state the breach and recommend escalation "
                    "rather than hiding uncertainty."
                ),
            },
        ],
    },
    # ----- 02 Support Policy v2 (DEPRECATED) ------------------------------
    {
        "code": "POL-SUPPORT-V2",
        "title": "ParcelPilot Support Policy v2 (DEPRECATED)",
        "source_type": SourceType.DEPRECATED,
        "status": "deprecated",
        "version": "v2",
        "effective_date": "2025-01-01",
        "account_code": None,
        "internal_only": True,
        "source_file": "02_Support_Policy_v2_DEPRECATED.pdf",
        "sections": [
            {
                "heading": "Severity and response targets (SUPERSEDED)",
                "content": (
                    "DEPRECATED — DO NOT USE FOR CURRENT REQUESTS. Superseded by Support Policy v3 "
                    "effective 1 May 2026. Retained for historical reference only.\n"
                    "Enterprise — P1: 1 hour; P2: 4 hours; P3: 2 business days.\n"
                    "Growth — P1: 4 business hours; P2: 1 business day; P3: 3 business days.\n"
                    "Standard — P1: 8 business hours; P2: 2 business days; P3: 3 business days."
                ),
            },
        ],
    },
    # ----- 03 Cancellation & Service Credit SOP v4 (CURRENT) --------------
    {
        "code": "SOP-CANCEL-CREDIT-V4",
        "title": "ParcelPilot Cancellation & Service Credit SOP v4",
        "source_type": SourceType.SOP,
        "status": "current",
        "version": "v4",
        "effective_date": "2026-06-15",
        "account_code": None,
        "internal_only": False,
        "source_file": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
        "sections": [
            {
                "heading": "§1 Order cancellation",
                "content": (
                    "DRAFT: May be cancelled with no fee. "
                    "BOOKED, not yet PICKED_UP: May be cancelled. No fee within 30 minutes of "
                    "booking. After 30 minutes, charge INR 250 unless a customer agreement "
                    "explicitly waives the cancellation fee. "
                    "PICKED_UP: Do not cancel. Use the return-to-origin workflow if the customer "
                    "wants the parcel returned. "
                    "DELIVERED: Cannot be cancelled."
                ),
            },
            {
                "heading": "§2 Failed-pickup service credits",
                "content": (
                    "Under the default policy, a customer is eligible for a service credit when the "
                    "pickup is more than 2 hours past the end of the scheduled pickup window, the "
                    "carrier is at fault, and there is no customer-caused issue. The default credit "
                    "is the lower of INR 500 or 10% of the shipment fee. A signed customer agreement "
                    "may replace the default delay threshold, credit amount, or cap."
                ),
            },
            {
                "heading": "§3 Approval and uncertainty",
                "content": (
                    "Any individual credit above INR 1,000 requires manager approval. Do not promise "
                    "a credit when carrier fault, pickup timing, or customer fault is unknown. When "
                    "data conflicts, identify the conflict and request verification before a "
                    "state-changing action."
                ),
            },
        ],
    },
    # ----- 04 Product Operations Guide & Known Issues (CURRENT) -----------
    {
        "code": "OPS-GUIDE-KI",
        "title": "ParcelPilot Product Operations Guide & Known Issues",
        "source_type": SourceType.OPERATIONAL_GUIDE,
        "status": "current",
        "version": "2026-08-14",
        "effective_date": "2026-08-14",
        "account_code": None,
        "internal_only": True,
        "source_file": "04_Product_Operations_Guide_and_Known_Issues.pdf",
        "sections": [
            {
                "heading": "§1 Plan capabilities",
                "content": (
                    "Bulk Upload: Available on Growth and Enterprise. Supported file size is up to "
                    "5,000 rows per CSV. Standard: Bulk Upload is not included. "
                    "Shipment status: BOOKED means the shipment is created but ParcelPilot has not "
                    "yet received a pickup confirmation. PICKED_UP means carrier pickup has been "
                    "confirmed."
                ),
            },
            {
                "heading": "§2 Known issue KI-208 — Bulk Upload failures on large CSVs",
                "content": (
                    "Opened 10 August 2026, Status: Investigating. Some Growth and Enterprise "
                    "customers experience intermittent failures on CSV uploads above approximately "
                    "3,000 rows, even though the supported product limit remains 5,000 rows. "
                    "Workaround: split the upload into files below 3,000 rows. Individual shipment "
                    "creation is unaffected."
                ),
            },
            {
                "heading": "§2 Known issue KI-211 — SwiftShip pickup webhook delay",
                "content": (
                    "Opened 12 August 2026, Status: Monitoring. SwiftShip pickup confirmation "
                    "webhooks can arrive up to 20 minutes late. A parcel may physically be collected "
                    "while ParcelPilot still shows BOOKED. Before telling a customer that a pickup "
                    "did not occur, verify the carrier status or wait through the known delay window."
                ),
            },
            {
                "heading": "§3 Resolved issue KI-176 — Address validation",
                "content": (
                    "Resolved 18 July 2026. Do not use this resolved issue to explain new incidents "
                    "unless evidence specifically matches it."
                ),
            },
        ],
    },
    # ----- 05 Northstar Enterprise Agreement (CURRENT, ACCT-001) ----------
    {
        "code": "AGR-NORTHSTAR",
        "title": "ParcelPilot — Northstar Logistics Enterprise Agreement",
        "source_type": SourceType.CUSTOMER_AGREEMENT,
        "status": "current",
        "version": "2026",
        "effective_date": "2026-01-01",
        "account_code": "ACCT-001",
        "internal_only": False,
        "source_file": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
        "sections": [
            {
                "heading": "§1 Support terms",
                "content": (
                    "For Northstar Logistics (ACCT-001), the following first-response targets replace "
                    "ParcelPilot's standard support-policy targets: P1: 15 minutes, 24x7; P2: 1 hour; "
                    "P3: 8 business hours."
                ),
            },
            {
                "heading": "§2 Shipment cancellation",
                "content": (
                    "Northstar may cancel any BOOKED shipment before pickup with no cancellation fee, "
                    "regardless of how long ago the shipment was booked. Once a shipment is PICKED_UP, "
                    "the standard return-to-origin process applies."
                ),
            },
            {
                "heading": "§3 Service credits",
                "content": (
                    "Monthly aggregate service credits are capped at INR 5,000. Unless this agreement "
                    "states otherwise, the current ParcelPilot service-credit SOP applies."
                ),
            },
            {
                "heading": "§4 Account contact",
                "content": "Dedicated CSM: Priya Mehta. Term: 1 January 2026 to 31 December 2026. Status: ACTIVE.",
            },
        ],
    },
    # ----- 06 LumenWorks Service Agreement (CURRENT, ACCT-002) ------------
    {
        "code": "AGR-LUMENWORKS",
        "title": "ParcelPilot — LumenWorks Service Agreement",
        "source_type": SourceType.CUSTOMER_AGREEMENT,
        "status": "current",
        "version": "2026",
        "effective_date": "2026-03-01",
        "account_code": "ACCT-002",
        "internal_only": False,
        "source_file": "06_LumenWorks_Service_Agreement.pdf",
        "sections": [
            {
                "heading": "§1 Support terms",
                "content": (
                    "For LumenWorks (ACCT-002, Growth plan): P1: 2 business hours; P2: 4 business "
                    "hours; P3: 2 business days. No weekend or after-hours support coverage."
                ),
            },
            {
                "heading": "§2 Cancellation terms",
                "content": (
                    "No special cancellation-fee waiver applies. Use the current ParcelPilot "
                    "Cancellation & Service Credit SOP."
                ),
            },
            {
                "heading": "§3 Failed-pickup credits",
                "content": (
                    "If a pickup is more than 4 hours past the end of the scheduled pickup window, "
                    "the carrier is at fault, and the customer is not at fault, LumenWorks receives a "
                    "fixed INR 300 service credit. This clause replaces the default failed-pickup "
                    "credit amount and timing threshold in the SOP."
                ),
            },
        ],
    },
]
