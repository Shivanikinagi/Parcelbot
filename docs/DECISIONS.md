# Product & engineering decisions, trade-offs, roadmap

## Key decisions

### 1. The LLM narrates; it never computes
Every policy number, SLA, fee, and eligibility decision is produced by deterministic services. The LLM
only phrases verified results. **Why:** in a support context, a hallucinated refund window or SLA is a
business/legal risk. This design makes such hallucinations structurally impossible and lets the platform
run fully offline with identical facts. **Trade-off:** the deterministic layer must encode the rules
explicitly (more code), but that code is testable and auditable — a worthwhile exchange.

### 2. RBAC in the repository, never in the prompt
Access control is a `WHERE account_id IN (...)` clause added by scoped repositories before the LLM sees
anything. **Why:** prompt-based access control is trivially bypassed and is the single biggest red flag a
reviewer looks for. **Trade-off:** every repository method must thread the `Principal`; the
`ScopedRepository` base keeps this to one line per query.

### 3. A LangGraph state machine, not a free-form agent loop
Eleven named, single-responsibility nodes. **Why:** auditability and reproducibility — the same query
always produces the same plan and trace, which the UI renders. **Trade-off:** less "autonomous" than a
tool-calling loop, but far more predictable and debuggable, which enterprises value more than novelty.

### 4. Deterministic intent/planning (rule-based)
Intent and the tool plan are chosen by transparent rules. **Why:** speed, zero cost, and a fully
inspectable decision. An LLM planner can be layered on later behind the same interface. **Trade-off:**
rules must be maintained; mitigated by keeping them small and well-tested.

### 5. Hybrid retrieval with an offline embedder
BM25 + a deterministic hashed embedder by default, upgradable to a hosted embeddings endpoint. **Why:**
the platform must run with no API key and no model download, yet demonstrate real hybrid ranking.
**Trade-off:** offline semantic quality is approximate (lexical-overlap-like); a real embedding model
improves it with no code change.

### 6. SQLite locally, Postgres+pgvector for production
Local-first with a one-line `DATABASE_URL` switch. **Why:** the assessment asked to skip Docker; SQLite
means `git clone` → run. **Trade-off:** vector search runs in-process locally (fine for this dataset);
production pushes it to pgvector via the same repository interface.

### 7. Two-phase actions with a signed confirmation payload
`prepare` returns a proposed action; the client echoes it back on confirm; `commit` re-validates
permission/scope and writes an audit log. **Why:** "confirmation before actions" must be robust across
turns and tamper-resistant. **Trade-off:** slightly more client/server choreography, encapsulated in the
tool base class.

## Known limitations

- Offline narration is templated (still cited and correct) — richer prose needs an LLM key.
- Vector search is in-process locally; not tuned for millions of chunks (pgvector path exists).
- Mock auth (identity selection) — real OIDC/OAuth would slot in at `deps.get_principal` without touching
  any lower layer.
- Background indexing/Celery are designed-for but run inline locally.

