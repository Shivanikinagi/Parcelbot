# API reference

Base path: `/api`. All endpoints except `/auth/login` and `/auth/users` require an
`Authorization: Bearer <token>` header. Interactive docs are available at `/docs` (Swagger) and
`/redoc` when the backend is running.

Every response is scoped to the caller's `Principal`; forbidden access returns `403`/`404` without
leaking existence, and errors are `{"error": {"code, message, details}}` with no stack traces.

## Auth

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/auth/login` | public | Body `{email}` → `{token, user}`. Mock auth (identity selection); token is HMAC-signed. |
| GET | `/auth/me` | any | Current user. |
| GET | `/auth/users` | public | Seeded demo identities (for the login screen). |

## Chat

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/chat/message` | any | **SSE stream.** Body `{message, conversation_id?, confirm_action?}`. Emits `start` → `meta` → `token*` → `done` events. Pass `confirm_action` to execute a previously prepared state change. |

`meta` event payload: `{intent, summary, recommendation, confidence, confidence_band, citations[],
conflicts[], trace[], tool_calls[], evidence[], pending_action, escalation, committed}`.

## Conversations

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/conversations` | any | List the caller's conversations (managers see all). |
| POST | `/conversations` | any | Create an empty conversation. |
| GET | `/conversations/{id}/messages` | owner/manager | Full message history with per-message `meta`. |
| PATCH | `/conversations/{id}/title` | owner/manager | Rename. |
| PATCH | `/conversations/{id}/pin` | owner/manager | Pin/unpin. |

## Catalog (RBAC-scoped)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/accounts` | any | Accounts in scope. |
| GET | `/orders` · `/orders/{code}` | any | Orders in scope. |
| GET | `/tickets` | any | Tickets in scope, with live SLA on open tickets. |
| GET | `/tickets/{code}` | any | Ticket detail: classified severity, SLA, known-issue matches, historical resolution. |
| GET | `/agreements/{account_code}` | in-scope | Account + its current agreement terms. |

## Operations & analytics (internal)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/ops/dashboard` | support+ | KPIs, AI insights, high-severity tickets, SLA breaches, recurring problems, carrier problems, customer health, escalations, investigations. |
| GET | `/analytics` | manager+ | Ticket volume, severity/status distributions, SLA compliance, top issues, carrier failures, support load, top customers. |

## Knowledge

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/knowledge/documents` | any | Documents visible to the caller. |
| GET | `/knowledge/search?q=` | any | Hybrid retrieval: ranked passages, citations, detected conflicts. |

## Audit & observability

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/audit` | manager+ | Immutable audit trail of state changes. |
| GET | `/tools/executions` | support+ | Per-tool telemetry (latency, success, summary). |

## System

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/health` | public | Liveness. |
| GET | `/system/info` | any | LLM mode (mock/live), model, embeddings mode, reference time, role. |
