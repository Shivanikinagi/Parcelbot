# Deployment guide

The app is two deployables: a **FastAPI** backend and a **Next.js** frontend. It runs locally with no
Docker; for hosting, the recommended split is **Vercel (frontend) + Render/Fly.io/Railway (backend +
Postgres)**.

## Environment variables

### Backend (`backend/.env`)
| Var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/parcelpilot.db` | Use `postgresql+psycopg://…` in production. |
| `LLM_API_KEY` | *(empty)* | OpenRouter key; empty → offline mock. |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible. |
| `LLM_MODEL` | `openai/gpt-4o-mini` | Any model on your OpenRouter account. |
| `EMBEDDINGS_BASE_URL` / `EMBEDDINGS_API_KEY` | *(empty)* | Optional hosted embeddings; empty → local embedder. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated; set to the deployed frontend origin. |
| `AUTH_SECRET` | `dev-secret-change-me` | **Change in production** (signs session tokens). |
| `REFERENCE_TIME` | `2026-08-16 11:00` | Dataset snapshot; keep for the assessment data. |

### Frontend (`frontend/.env.local`)
| Var | Default | Notes |
|---|---|---|
| `BACKEND_ORIGIN` | `http://127.0.0.1:8000` | Backend origin the Next server proxies `/api/*` to. |

## Local (no Docker)

```bash
# terminal 1
cd backend && python -m venv .venv && . .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt && uvicorn app.main:app --port 8000
# terminal 2
cd frontend && npm install && npm run dev
```

The backend auto-seeds the real dataset on first start.

## Production

### Backend (Render / Fly.io / Railway)
1. Provision **Postgres** (Render/Fly/Railway managed); enable the `vector` extension for pgvector.
2. Set env vars (above) — `DATABASE_URL`, `AUTH_SECRET`, `CORS_ORIGINS`, and optionally `LLM_API_KEY`.
3. Build: `pip install -r requirements.txt`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Run the seed once (`python -m app.db.seed`) or rely on the empty-DB auto-seed on first boot.

### Frontend (Vercel)
1. Root directory `frontend`. Framework preset: Next.js.
2. Set `BACKEND_ORIGIN` to the deployed backend URL.
3. Deploy — the `rewrites()` in `next.config.mjs` proxy `/api/*` to the backend, so the browser only ever
   talks to one origin (no CORS in the browser; the backend still restricts `CORS_ORIGINS` for direct
   calls).

### Docker (optional, later)
The stack is Docker-friendly: a `backend` service (uvicorn), a `web` service (`next start`), Postgres +
pgvector, and optionally Redis for Celery. A `docker-compose.yml` can be added without code changes —
only `DATABASE_URL`/`BACKEND_ORIGIN` differ.

## Health & observability
- `GET /api/health` for liveness probes.
- Structured JSON logs (one object per line) with `request_id` — ship to any log aggregator.
- `GET /api/tools/executions` and `GET /api/audit` expose per-tool latency and the action audit trail.
