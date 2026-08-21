"""Severity classification (P1/P2/P3) from ticket text.

The dataset deliberately omits severity — an agent must infer it from the
description using the current Support Policy §2 definitions. This is a
transparent, rule-based classifier (auditable, deterministic) rather than an
opaque LLM call, so every decision cites the signals that drove it.
"""

from __future__ import annotations

import re

from app.schemas.results import SeverityResult

# Ordered signal tables. Each (pattern, human-signal) — first-tier P1 wins.
_P1_SIGNALS: list[tuple[str, str]] = [
    (r"\ball\b.*\b(fail|failing|down|broken)\b", "all operations failing"),
    (r"\b(complete|total)\b.*\boutage\b", "complete outage"),
    (r"\boutage\b", "service outage"),
    (r"\bhttp\s*500\b|\b500 error\b|\berror 500\b", "HTTP 500 on core action"),
    (r"\bcannot (create|book)\b|\bunable to (create|book)\b", "cannot create shipments"),
    (r"\bcredential|api key|api-key|secret|token\b.*\b(expos|leak|post|screenshot)", "credential exposure"),
    (r"\b(api key|credential).*(expos|leak)|(expos|leak).*(api key|credential)", "credential exposure"),
    (r"\bsecurity (incident|breach)\b|\bsuspected (breach|exposure)\b", "security incident"),
]
_P2_SIGNALS: list[tuple[str, str]] = [
    (r"bulk upload.{0,40}fail\w*", "bulk upload failing (major feature degraded)"),
    (r"upload.{0,20}fail\w*|fail\w*.{0,20}upload", "upload failure"),
    (r"degrad\w+", "feature degraded"),
    (r"intermittent", "intermittent failures"),
    (r"\bmajor\b.{0,20}(feature|issue)", "major feature affected"),
    (r"workaround|one-?by-?one still works|still works", "workaround exists"),
    (r"roughly \d+%|\b\d+%\b.{0,20}fail|partial\w*", "partial failure"),
]
_P3_SIGNALS: list[tuple[str, str]] = [
    (r"\bhow (do|to|can)\b", "how-to question"),
    (r"\bchange\b.*\b(contact|email|setting|config)\b", "configuration request"),
    (r"\bbilling contact\b", "account configuration"),
    (r"\bquestion\b", "general question"),
]


def _match(text: str, table: list[tuple[str, str]]) -> list[str]:
    hits = []
    for pattern, signal in table:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(signal)
    return hits


def classify_severity(subject: str, description: str) -> SeverityResult:
    text = f"{subject}\n{description}"
    p1 = _match(text, _P1_SIGNALS)
    p2 = _match(text, _P2_SIGNALS)
    p3 = _match(text, _P3_SIGNALS)

    if p1:
        return SeverityResult(
            severity="P1",
            label="Critical",
            rationale=(
                "Matches Support Policy §2 P1 (complete outage, or confirmed/suspected "
                "security incident with immediate material risk)."
            ),
            signals=p1,
            confidence=0.9,
        )
    if p2:
        return SeverityResult(
            severity="P2",
            label="High",
            rationale=(
                "Matches Support Policy §2 P2 (major feature degraded but a workaround "
                "or core operation remains)."
            ),
            signals=p2,
            confidence=0.8,
        )
    if p3:
        return SeverityResult(
            severity="P3",
            label="Normal",
            rationale="Matches Support Policy §2 P3 (how-to, configuration, or limited-impact issue).",
            signals=p3,
            confidence=0.75,
        )
    # Default to P3 with low confidence when nothing clearly matches.
    return SeverityResult(
        severity="P3",
        label="Normal",
        rationale="No strong P1/P2 signals detected; defaulting to P3 with low confidence.",
        signals=["no decisive signal"],
        confidence=0.4,
    )
