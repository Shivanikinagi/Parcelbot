"""FastAPI application factory and entrypoint.

Wires middleware, CORS, error handlers, and all routers. On startup it ensures
the schema exists and seeds the real assessment dataset if the database is
empty — so a fresh clone runs with a single command and no manual steps.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_principal
from app.api.errors import install_error_handlers
from app.api.middleware import RequestIdMiddleware
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.security import Principal

logger = get_logger(__name__)


def _ensure_seeded() -> None:
    from sqlalchemy import func, select

    from app.db.base import Base, SessionLocal, engine
    from app.models.organization import User

    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        count = session.scalar(select(func.count(User.id))) or 0
    if count == 0:
        logger.info("Empty database detected — seeding the assessment dataset.")
        from app.db.seed import seed

        seed()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    _ensure_seeded()
    mode = "OFFLINE MOCK" if settings.use_mock_llm else f"LIVE ({settings.llm_model})"
    logger.info("ParcelPilot API starting — LLM mode: %s", mode)
    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="ParcelPilot Support Intelligence API",
        version="1.0.0",
        description="Enterprise AI support platform — RAG, agentic reasoning, RBAC, and audited actions.",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    install_error_handlers(app)

    # Routers
    from app.api.routers import (
        audit,
        auth,
        catalog,
        chat,
        conversations,
        knowledge,
        ops,
    )

    for module in (auth, chat, conversations, catalog, ops, audit, knowledge):
        app.include_router(module.router, prefix="/api")

    @app.get("/api/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/system/info", tags=["system"])
    def system_info(principal: Principal = Depends(get_principal)) -> dict:
        return {
            "llm_mode": "mock" if settings.use_mock_llm else "live",
            "llm_model": None if settings.use_mock_llm else settings.llm_model,
            "embeddings": "remote" if settings.use_remote_embeddings else "local",
            "reference_time": settings.reference_time,
            "role": principal.role.value,
        }

    return app


app = create_app()
