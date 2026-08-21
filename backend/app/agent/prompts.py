"""System prompt and narration prompt builder.

The system prompt is a hard guardrail: the LLM may only phrase facts that the
deterministic layer already computed and the evidence already supports. It is
explicitly told it cannot introduce policy numbers, that historical tickets are
context-only, and that pending actions must be surfaced for confirmation — this
is prompt-injection- and hallucination-resistant because the *authority* for
every number lives in code, not in the prompt.
"""

from __future__ import annotations

import json

from app.agent.state import AgentState

SYSTEM_PROMPT = """You are ParcelPilot's AI Support Intelligence assistant.

Rules you MUST follow:
1. Use ONLY the VERIFIED FACTS and EVIDENCE provided below. Never invent or alter
   policy numbers, SLA targets, fees, credit amounts, dates, or eligibility.
2. Cite sources inline using their [S#] markers from the SOURCES list.
3. If sources conflict, explain the conflict briefly and state which source wins
   and why (a signed customer agreement outranks the current policy, which
   outranks deprecated documents; historical tickets are context only and may be
   wrong).
3b. A customer agreement's terms apply ONLY to that specific customer. If the
    user's question is general/unscoped (no specific ticket, order, or account
    named) and the retrieved evidence includes one customer's agreement
    clause, DO NOT present that clause as the universal answer. Lead with the
    general policy default instead, and mention the agreement override only as
    a secondary note (e.g. "the default is X; note that [Customer]'s contract
    sets Y instead"). Only lead with an agreement's terms when the question is
    clearly about that specific account.
4. If an ACTION IS PENDING, do not claim it is done. Clearly summarise what will
   happen, list the consequences, and ask the user to confirm.
5. If confidence is low or a fact is unknown, say so plainly and recommend
   escalation rather than guessing.
6. Be concise, professional, and helpful. Use short paragraphs and bullets.
   Respond in Markdown. Amounts are in INR.
7. RECENT CONVERSATION (if provided) is for continuity only — e.g. answering
   "why did you choose that?" by referencing what was just discussed. Never
   pull a *new* fact from it; every factual claim must still trace to this
   turn's VERIFIED FACTS or RETRIEVED EVIDENCE.
"""


def build_narration_messages(state: AgentState) -> list[dict]:
    answer = state.get("answer", {})
    facts = answer.get("key_facts", [])
    conflicts = state.get("conflicts", [])
    citations = state.get("citations", [])
    pending = state.get("pending_action")
    escalation = state.get("escalation")

    doc = state.get("results", {}).get("document_search")
    context_block = doc.data.get("context_block", "") if doc else ""

    sources_lines = [
        f"[{c['marker']}] {c['title']} — {c['heading']} "
        f"(source_type={c['source_type']}, status={c['status']}, authority_rank={c['authority_rank']})"
        for c in citations
    ]

    payload = {
        "user_question": state["query"],
        "verified_facts": facts,
        "conflicts": [
            {"topic": c["topic"], "resolution": c["resolution"], "resolved_value": c.get("resolved_value")}
            for c in conflicts
        ],
        "recommendation": answer.get("recommendation", ""),
        "escalation": escalation,
        "pending_action": pending,
        "confidence": answer.get("confidence"),
    }

    history = state.get("history", [])[-4:]
    history_lines = [f"{m['role']}: {m['content'][:400]}" for m in history if m.get("content")]

    user = (
        "RECENT CONVERSATION (continuity only, not a source of new facts):\n"
        + ("\n".join(history_lines) or "(this is the first message in the conversation)")
        + "\n\nVERIFIED FACTS AND CONTEXT (authoritative — do not contradict):\n"
        + json.dumps(payload, indent=2)
        + "\n\nRETRIEVED EVIDENCE:\n"
        + (context_block or "(no passages retrieved)")
        + "\n\nSOURCES:\n"
        + ("\n".join(sources_lines) or "(none)")
        + "\n\nWrite the reply to the user now, following all rules."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
