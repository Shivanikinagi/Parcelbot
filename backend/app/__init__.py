"""ParcelPilot — AI Support Intelligence Platform (backend).

Clean-architecture layers (outer depends on inner, never the reverse):

    api/          Presentation — FastAPI routers, request/response wiring
    agent/        Agent Layer  — LangGraph orchestration of the support brain
    tools/        Tool Layer   — typed, validated capabilities the agent invokes
    services/     Service Layer— business rules (SLA, escalation, conflicts)
    repositories/ Repository   — the ONLY place data is read/written; RBAC lives here
    models/       Domain       — SQLAlchemy ORM entities
    db/           Infrastructure — engine, session, seed
"""

__version__ = "1.0.0"
