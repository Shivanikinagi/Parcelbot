# AI Tool Usage

**Claude Code** (Anthropic's CLI agent, running Claude Sonnet 5) was used for the large majority of this
project's design and implementation, in an interactive, iterative session — not a single "generate the
whole app" prompt.

## How it was used

- **Architecture and design**: the layered architecture (presentation → agent → tools → services →
  repositories → data), the RBAC-in-the-repository-layer decision, the source-authority ranking, and the
  LangGraph node breakdown were designed collaboratively — I set the constraints and reviewed the
  approach; Claude proposed and I approved the concrete structure.
- **Reading the real assessment data pack**: Claude read all 6 PDFs and the workbook directly, extracted
  the actual policy numbers, SLA tables, and per-account agreement terms, and built the knowledge base
  and structured seed data from that — not from invented placeholder data.
- **Code generation**: the backend (FastAPI, LangGraph, SQLAlchemy, retrieval, services, tools) and
  frontend (Next.js, Tailwind, the design system, all pages) were written by Claude, file by file, with
  me directing scope and priorities between steps.
- **Verification, not trust-on-faith**: after each major component, Claude ran it — pytest for the
  backend logic, a live agent smoke test against the real dataset's engineered conflicts, a full
  browser-driven walkthrough of the running UI (login → streaming chat → confirmation → committed
  escalation, verified against the database afterward), and a TypeScript build of the frontend. Claims in
  this repo's docs are backed by commands that were actually run, not assumed.
- **Adversarial self-review**: when I later supplied a rigorous 25-category QA test plan covering RBAC,
  prompt-injection resistance, hallucination probes, and multi-turn conversation behaviour, Claude built a
  test driver, ran it against the live app (including a live OpenRouter LLM and a real Neon Postgres
  database), and used the actual results — including a genuine weakness it found (loss of context on
  follow-up questions) — rather than presenting an idealised picture.
- **Debugging real integration issues**: e.g. diagnosing that a Neon Postgres connection string needed an
  explicit `+psycopg` SQLAlchemy driver suffix, and that Windows port conflicts from earlier dev-server
  runs were blocking new ones — both found and fixed by inspecting actual error output, not guessed.

## What I did myself

- Supplied the real assessment brief and data pack.
- Made the product decisions Claude explicitly asked for rather than guessed: LLM provider (OpenRouter)
  and key, hosting platform choice (Render), local-first vs. Docker, and how to reconcile the Git history
  once I'd made edits directly on GitHub.
- Provisioned the Neon Postgres database and the OpenRouter API key myself and wired them into the
  backend's `.env`.
- Ran the QA test plan above and reviewed the evidence-based findings before deciding what to fix and
  what to document as a known limitation.

## Why this matters for evaluating the submission

Every specific claim in this repo's documentation (test counts, live-tested example answers, confirmed
RBAC boundaries, the one weakness disclosed in the Product Note) reflects an actual command that was run
against the actual running system in this session, not a description of intended behaviour.
