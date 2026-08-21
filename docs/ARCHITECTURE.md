# Architecture

ParcelPilot follows **clean layered architecture**: each layer depends only on the layer directly
beneath it, and the dependency arrows never reverse. This keeps the security-critical logic (RBAC) at
the bottom where it cannot be bypassed, and keeps the LLM at the top where it can only *phrase* what the
lower layers have already verified.

```
Presentation (Next.js)                         frontend/src
        │  HTTPS · SSE
Presentation (FastAPI routers, auth, SSE)      app/api
        │
Agent Layer (LangGraph orchestration)          app/agent
        │
Tool Layer (typed, validated capabilities)     app/tools
        │
Service Layer (deterministic business rules)   app/services
        │                         Retrieval    app/retrieval
Repository Layer  ★ RBAC enforced here ★        app/repositories
        │
Infrastructure (ORM models, engine, seed)      app/models, app/db
        │
Database (SQLite local / Postgres+pgvector)
```

## Layer responsibilities

### Presentation — `app/api`
FastAPI routers translate HTTP into calls on the agent/services. Concerns handled here: authentication
(`deps.get_principal`), request-ID correlation middleware, rate limiting, CORS, SSE streaming, and
mapping domain exceptions to clean JSON (`errors.py`). No business logic lives here.

### Agent Layer — `app/agent`
A compiled **LangGraph** `StateGraph` with eleven nodes (see [AGENT.md](AGENT.md)). It orchestrates
tools, synthesises an explainable structured answer, and prepares (never auto-executes) actions. The
**Narrator** converts the structured answer to prose — via the LLM when a key is present, or a
deterministic template offline.

### Tool Layer — `app/tools`
Each tool declares a Pydantic **input schema**, a **required permission**, and whether it is
**state-changing**. The `Tool.execute` wrapper uniformly enforces validation, RBAC, timing, telemetry
(`tool_executions`), and error containment. State-changing tools implement `prepare` (returns a proposed
action, no mutation) and `commit` (mutates + writes an audit log).

### Service Layer — `app/services`
The deterministic brain. `severity_service`, `sla_service`, `cancellation_service`,
`service_credit_service`, `conflict_service`, `known_issues`, and `analytics_service` compute every
number and eligibility decision from structured data + policy constants (`app/db/policy_data.py`). They
return typed results (`app/schemas/results.py`) carrying citations and conflicts.

### Retrieval — `app/retrieval`
`HybridRetriever` blends BM25 (lexical) and vector (semantic) similarity, applies authority and freshness
weighting, runs MMR for diversity, and returns per-chunk score breakdowns plus a retrieval confidence.
Candidate chunks come pre-filtered by RBAC from `KnowledgeRepository`.

### Repository Layer — `app/repositories` ★
**The single gateway to data, and the only place access control lives.** `ScopedRepository` holds the
`Principal` and applies `WHERE account_id IN (...)` to every query. `KnowledgeRepository` additionally
filters `internal_only` chunks for customers. There is no code path from a tool or the agent to the ORM
that does not pass through a scoped repository.

### Infrastructure — `app/models`, `app/db`
SQLAlchemy 2.0 ORM models, the engine/session factory (SQLite by default with FK + WAL pragmas), and the
deterministic `seed` that loads the real assessment workbook, classifies ticket severities, and builds
the embedded knowledge base.

## Local vs. production profiles

| Concern | Local (default) | Production |
|---|---|---|
| Database | SQLite file | Postgres (`DATABASE_URL` env) |
| Vector search | In-process cosine over JSON embeddings | pgvector column + SQL similarity |
| Embeddings | Deterministic hashed embedder | OpenAI-compatible endpoint (`EMBEDDINGS_*`) |
| LLM | Offline template narrator | OpenRouter chat completions (`LLM_API_KEY`) |
| Background work | Inline | Celery + Redis (designed-for) |

The repository and retrieval layers are dialect-agnostic, so switching to Postgres+pgvector is a
configuration change, not a rewrite.

## Cross-cutting concerns

- **Logging** (`app/core/logging.py`): structured JSON with a per-request `request_id` woven into every
  line and audit row.
- **Config** (`app/core/config.py`): a single validated `Settings` singleton; nothing reads `os.environ`
  directly.
- **Clock** (`app/core/clock.py`): all time math uses the fixed dataset snapshot and a business-hours
  engine (Mon–Fri 09:00–18:00 IST), making results deterministic and reproducible.
- **Errors** (`app/core/exceptions.py`): typed domain errors map to HTTP status codes; clients never see
  stack traces.
