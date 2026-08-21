"""Turn the agent's structured answer into streamed prose.

Real mode streams tokens from the LLM (constrained by the system prompt to the
verified facts). Offline mode composes a deterministic Markdown reply from the
same structured answer — so the platform produces genuinely useful, cited
responses with no API key. Either way the *substance* is identical; only the
phrasing differs.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.agent.prompts import build_narration_messages
from app.agent.state import AgentState
from app.ai.llm import get_llm
from app.core.logging import get_logger

logger = get_logger(__name__)


def stream_narration(state: AgentState) -> Iterator[str]:
    """Yield chunks of the final reply."""
    llm = get_llm()
    if llm.available:
        try:
            yielded = False
            for chunk in llm.stream(build_narration_messages(state)):
                yielded = True
                yield chunk
            if yielded:
                return
        except Exception:  # noqa: BLE001 — degrade gracefully to the template
            logger.warning("LLM narration failed; falling back to template.", exc_info=True)
    # Offline / fallback: stream the deterministic template word-by-word.
    text = compose_template(state)
    for token in re.findall(r"\S+\s*", text):
        yield token


def compose_template(state: AgentState) -> str:
    answer = state.get("answer", {})
    intent = state.get("intent", {}).get("type")

    if state.get("committed"):
        return f"✅ {answer.get('summary', 'Action completed.')}"
    if state.get("error"):
        return answer.get("summary", state["error"])
    if intent == "greeting":
        return answer.get("summary", "Hello! How can I help with ParcelPilot support today?")

    parts: list[str] = []
    facts = answer.get("key_facts", [])
    citations = state.get("citations", [])
    cite_by_type = {c["source_type"]: c["marker"] for c in citations}

    # 1. Lead answer.
    if facts:
        parts.append(f"**{facts[0]}**")
        if len(facts) > 1:
            parts.append("\n".join(f"- {f}" for f in facts[1:]))
    else:
        doc = state.get("results", {}).get("document_search")
        passages = doc.data.get("passages", []) if doc else []
        if passages:
            top = passages[0]
            parts.append(f"Based on **{top['title']} — {top['heading']}** [{cite_by_type.get(top['source_type'], 'S1')}]:")
            parts.append(f"> {top['content']}")
        else:
            parts.append(answer.get("summary", "I couldn't find relevant information for that request."))

    # 2. Known-issue guidance from evidence.
    for ev in state.get("evidence", []):
        if ev["kind"] == "document" and ev["label"].startswith("KI-"):
            parts.append(f"**{ev['label']}** — {ev['detail']}")

    # 3. Conflicts.
    conflicts = state.get("conflicts", [])
    if conflicts:
        lines = ["**⚠️ Conflicting sources — resolved by authority:**"]
        for c in conflicts:
            src = "; ".join(f"{s['label']} → {s['value']}" for s in c.get("sources", []))
            lines.append(f"- *{c['topic']}*: {src}. **Resolution:** {c['resolution']}")
        parts.append("\n".join(lines))

    # 4. Escalation recommendation.
    esc = state.get("escalation")
    if esc and esc.get("recommended"):
        parts.append(f"**Recommended action:** Escalate now — {esc['reason']}")

    # 5. Pending action → confirmation.
    pending = state.get("pending_action")
    if pending:
        cons = "\n".join(f"  - {c}" for c in pending.get("consequences", []))
        parts.append(
            f"**Confirmation required** before I proceed:\n\n> {pending['human']}\n\n"
            f"This will:\n{cons}\n\nReply **confirm** to proceed, or **cancel** to abort."
        )

    # 6. Sources.
    if citations:
        src = "; ".join(f"[{c['marker']}] {c['title']} — {c['heading']}" for c in citations)
        parts.append(f"\n_Sources: {src}_")

    return "\n\n".join(parts)
