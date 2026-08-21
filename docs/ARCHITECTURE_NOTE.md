# Architecture Note

A short, submission-format note. For full depth see [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`AGENT.md`](AGENT.md), and [`DATA_MODEL.md`](DATA_MODEL.md).

## Agent design

The agent is a **LangGraph `StateGraph`** with eleven single-responsibility nodes (`classify_intent →
authorize → build_plan → retrieve → query_structured → reason → resolve_conflicts → validate_action →
request_confirmation → generate_response → write_audit`), not a free-form tool-calling loop. Intent
classification and tool planning are **deterministic and rule-based** (regex-driven entity extraction +
a fixed intent→tools mapping), not LLM-driven. This was a deliberate choice: for a support system, a
reproducible, auditable plan is worth more than an autonomous-but-unpredictable one, and it means the
whole pipeline — including the "which tools to call" decision — runs and is testable **with no LLM at
all**. The LLM's only job is the final `generate_response` narration step, converting an already-computed,
already-cited structured answer into prose. This makes the system's factual correctness independent of
model quality or availability.

## Tool design

Thirteen tools behind one uniform base class (`Tool.execute`), which enforces validation (Pydantic input
schemas), RBAC (`required_permission` check against the caller's role), timing, and telemetry
identically for every tool — no tool can skip a safety check by omission. Three families:

- **Retrieval**: `document_search` (hybrid RAG), `known_issue_match`.
- **Structured lookup/calculation**: `order_lookup`, `ticket_lookup`, `agreement_lookup`,
  `customer_history`, `structured_data_query`, `sla_calculator`, `cancellation_evaluator`,
  `service_credit_evaluator`, `service_credit_scenario_evaluator`.
- **State-changing**: `escalation_creator`, `follow_up_task_creator`, `ticket_update` — each implements
  `prepare` (returns a proposed action, no mutation) and a separate `commit` (mutates + audits), reachable
  only after the client echoes back the exact prepared action on confirmation.

## Document and structured-data handling

Documents (policies, SOPs, the product guide, agreements, and closed/historical tickets) are chunked at
section granularity with denormalised ranking metadata (`source_type`, `authority_rank`, `status`,
`account_id`, `internal_only`) so retrieval scoring and RBAC filtering need no joins. `HybridRetriever`
blends BM25 (lexical) and cosine similarity (semantic, via a swappable embedder — deterministic offline
hashing by default, any OpenAI-compatible endpoint optionally) with `alpha`-weighted fusion, applies
authority + freshness multipliers, and runs MMR for result diversity.

Structured data (accounts, orders, tickets from the assessment workbook) is loaded by a deterministic
seed script into a normalised schema, with severity classified from ticket text (not present in the
source data) by a transparent, rule-based classifier. Per-account agreement overrides (SLA targets,
cancellation waivers, service-credit thresholds/amounts) are encoded as structured `terms` JSON on the
`Agreement` row, alongside the human-readable contract text — services read the structured terms
directly; citations still point back to the originating document/section.

## Source reliability and conflict handling

A fixed authority ranking governs every decision: **Customer Agreement (1) > Policy (2) > SOP (3) >
Operational Guide (4) > Structured Data (5) > Historical Tickets (6) > Deprecated (7)**. Two conflict
paths exist: (a) domain services (SLA/cancellation/service-credit) know their own precedence rules and
emit an explicit `Conflict` object naming every disagreeing source, its rank, and the resolution rule
when they detect one; (b) a retrieval-level `conflict_service` flags when a current source and a
deprecated/historical source were retrieved together for the same topic. Deprecated documents and closed
tickets are retrievable (so the agent can *reference* them to explain a conflict) but are authority- and
freshness-down-weighted in ranking and are never allowed to set the resolved value. Confidence is high for
deterministic computations, inherits the retriever's score for pure RAG answers, and is explicitly capped
when an eligibility guardrail can't be verified (e.g. carrier fault unconfirmed) — the system prefers
"I don't know, here's why" over a confident guess.

## Major technical trade-offs

| Decision | Trade-off accepted |
|---|---|
| Deterministic rule-based planner instead of LLM tool-calling | Less flexible on truly novel phrasing; fully reproducible, offline-capable, and auditable in exchange. |
| LLM narrates, never computes | Requires every business rule to be encoded in code (more upfront work); eliminates hallucinated numbers entirely. |
| RBAC in the repository layer | Every repository method must thread the `Principal`; in exchange, access control cannot be bypassed by prompt text. |
| SQLite locally / Postgres+pgvector in production | Zero-dependency local dev; vector search is in-process (fine at this data scale) rather than pushed to the DB. |
| Offline deterministic embedder by default | Semantic quality is lexical-overlap-approximate offline; upgradable to a real embedding model with no code change. |
| No cross-turn conversational memory in the LLM context (see Product Note) | Each turn's reasoning is independent and fully re-verifiable, at the cost of natural-sounding follow-up questions like "why did you choose that?" needing the entity restated. |
