"""Known-issue matcher (from the Product Operations Guide §2/§3).

Powers ticket triage ("does this match a known issue?") and the ops
dashboard's recurring-problems widget. Matching is keyword-based and returns
the operational guidance verbatim — including KI-211's crucial caveat that a
"still BOOKED" status may just be a delayed webhook, not a failed pickup.
"""

from __future__ import annotations

import re

KNOWN_ISSUES: list[dict] = [
    {
        "code": "KI-208",
        "title": "Bulk Upload failures on large CSVs",
        "status": "Investigating",
        "opened": "2026-08-10",
        "patterns": [r"bulk upload", r"\bcsv\b", r"3[,.]?000 rows", r"\d[,.]?\d{3}-row"],
        "plans": ["growth", "enterprise"],
        "guidance": (
            "Known issue KI-208: intermittent failures above ~3,000 rows even though the "
            "supported limit is 5,000. Workaround: split the upload into files below 3,000 "
            "rows. Individual shipment creation is unaffected."
        ),
    },
    {
        "code": "KI-211",
        "title": "SwiftShip pickup webhook delay",
        "status": "Monitoring",
        "opened": "2026-08-12",
        "patterns": [r"swiftship", r"still (shows|showing) booked", r"webhook", r"pickup.*booked"],
        "plans": [],
        "guidance": (
            "Known issue KI-211: SwiftShip pickup confirmation webhooks can arrive up to 20 "
            "minutes late, so a parcel may already be collected while ParcelPilot still shows "
            "BOOKED. Do NOT tell the customer the pickup failed — verify carrier status or wait "
            "through the known delay window first."
        ),
    },
    {
        "code": "KI-176",
        "title": "Address validation (RESOLVED)",
        "status": "Resolved",
        "opened": "2026-07-18",
        "patterns": [r"address validation"],
        "plans": [],
        "guidance": (
            "KI-176 was resolved on 18 July 2026. Do not use this resolved issue to explain new "
            "incidents unless the evidence specifically matches it."
        ),
    },
]


def match_known_issues(text: str, plan: str | None = None) -> list[dict]:
    """Return known issues whose patterns match ``text`` (optionally plan-filtered)."""
    matches: list[dict] = []
    lowered = text.lower()
    for issue in KNOWN_ISSUES:
        if issue["plans"] and plan and plan.lower() not in issue["plans"]:
            continue
        if any(re.search(p, lowered, flags=re.IGNORECASE) for p in issue["patterns"]):
            matches.append(issue)
    return matches
