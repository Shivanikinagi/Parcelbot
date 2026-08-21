# Product Note

## Which additional client problem I chose, and how I addressed it

I built for **both** additional problems, since they reinforce each other in a support product:

**Problem 2 — Trust and Reliability** was the priority. A support agent that occasionally hallucinates a
policy number is worse than no agent, so the entire architecture is organised around never letting that
happen: business rules are computed in code (not the LLM), every source disagreement is surfaced with an
explicit authority ranking rather than silently resolved, confidence is shown per-answer and is explicitly
capped when an eligibility guardrail can't be verified, and every state change requires confirmation and
writes an audit entry. See [`ARCHITECTURE_NOTE.md`](ARCHITECTURE_NOTE.md) for the mechanism.

**Problem 1 — Proactive Issue Detection** is the Operations dashboard: high-severity tickets, SLA
breaches, recurring known-issue clusters (with counts), carrier-fault patterns, per-account health
scores, recent escalations, and open investigations, plus a short "AI Insights" summary generated from
those same counted facts (never a free-floating LLM observation) — e.g. *"1 P1 SLA breached: TKT-501"*,
*"KI-208 is affecting 2 tickets."* Analytics adds ticket volume, severity/SLA-compliance distributions,
carrier failures, and support load, all computed from the database, not invented. **This is also reachable
directly from chat** (`analytics_tool`, internal roles only) — asking "which tickets are approaching SLA
breach?" or "analyze the support activity" pulls the same live, counted data rather than falling back to
generic policy retrieval.

## Fixed during adversarial QA hardening

Before finalising this submission I ran a 25-category adversarial QA pass against the live system (RBAC
bypass attempts, prompt injection, hallucination probes, multi-turn conversations, ambiguous requests) and
fixed everything it found, verified against the running app a second time:

- **Cross-turn memory** — a follow-up like *"why did you choose that SLA?"* now carries the ticket/order/
  account discussed in the prior turn forward, instead of losing context and retrieving something
  unrelated.
- **Chat-reachable proactive detection** — "analyze the support activity," "which tickets are approaching
  SLA breach," and similar now call the same live analytics the dashboard uses, instead of generic
  document retrieval.
- **Unscoped-query agreement bias** — a fully generic question (no ticket/order/account named) no longer
  gets answered with one customer's contract override presented as the universal policy; both the
  retrieval ranking and the narration prompt now require a specific account context before an agreement
  can lead the answer.
- **Ambiguous requests now ask for clarification** — "escalate it," "what is the SLA?", and "I have a
  problem with my pickup" (all missing the entity needed to act) now ask a direct clarifying question
  instead of silently falling back to unrelated retrieval.
- **Explicit refusal for cross-account probing by name** — asking about another customer *by company
  name* (not just by account code, which was already blocked) now gets a clear, honest refusal rather than
  an evasive non-answer.
- **A real "what can you help me with?" answer** and a clean acknowledgment for "actually, don't do that"
  — both previously fell through to an unrelated policy quote.
- **Audit entries now identify the specific actor** (user id, email, name), not just their role.
- **Conflict citations pick the topically-relevant source**, not just the highest-authority one that
  happened to be retrieved.

## Anything else I would build for ParcelPilot (prioritised)

1. **LLM-assisted planning as a fallback**, layered behind the deterministic planner, for queries the
   rule-based intent classifier can't confidently place — so novel phrasing degrades gracefully into a
   real attempt rather than RAG-only. Keep the deterministic path as the default for cost/speed/
   reproducibility; only escalate to an LLM planner when the rule-based one is unsure.
2. **Real order-execution actions** — actually cancelling a shipment or issuing a service credit (with the
   manager-approval routing for amounts over ₹1,000, which the eligibility logic already flags) — rather
   than stopping at escalation/task/ticket-update. This is what turns the assistant from advisory into
   operational.
3. **A feedback loop**: thumbs up/down on answers, stored against the conversation, reviewed weekly to
   catch retrieval misses and tune the hybrid-search weighting — the single highest-leverage way to
   improve answer quality over time without guessing.
4. **SLA breach alerting** (webhook/email/Slack when a P1 crosses its target) instead of only surfacing
   breaches when someone opens the dashboard or asks — closes the last mile of "proactive."
5. **Deeper multi-turn memory** — the current fix carries forward the last-mentioned entity; a longer
   rolling summary of the conversation would handle richer multi-turn threads (e.g. comparing two tickets
   discussed several turns apart).

## What I intentionally left out, and why

- **Docker / containerised deployment** — the assessment explicitly allows skipping it; I kept the app
  local-first (SQLite, in-process retrieval) so it runs with zero infra, and documented the one-line
  `DATABASE_URL` switch to Postgres+pgvector for anyone who wants it (now proven working against a real
  Neon Postgres instance).
- **Real OAuth/SSO** — mocked as explicitly permitted; the token is genuinely signed (HMAC), and every
  layer below authentication is real, so swapping in real auth only changes how the email is established.
- **Order-cancellation/credit *execution*** (see roadmap #3 above) — I stopped at the three required
  action types (escalation, follow-up task, ticket update) rather than also wiring "actually cancel the
  shipment," to keep the state-changing surface area small and fully tested rather than broad and thin.
- **Multi-language support, voice, and a mobile app** — out of scope for a first-round assessment; the
  chat UI is responsive but not mobile-optimised beyond that.
- **LLM-assisted planning** (see roadmap #1) — the deterministic planner covers the tested surface area
  well; an LLM fallback for genuinely novel phrasing is a deliberate next step, not a gap in what's here.

## The one metric I'd use to judge usefulness

**Self-serve resolution rate without escalation or a wrong-but-confident answer** — i.e., the percentage
of customer queries the agent answers correctly and completely on its own, out of all queries where a
correct answer *existed* in the source pack. This single number forces the two things that actually
matter in a trust-sensitive support product: coverage (does it actually help, not just retrieve text) and
honesty (a wrong confident answer must count as a failure, not a resolution — which is why I'd pair it
with a manual accuracy audit on a sample, not just "did the conversation end without escalation").
Everything else (latency, cost per query, CSAT) is a useful secondary metric, but this is the one that
would tell ParcelPilot whether to expand the agent's authority or pull it back.
