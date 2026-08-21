"""Structured JSON logging with per-request correlation IDs.

Every log line is a single JSON object so it can be shipped to Datadog /
CloudWatch / Loki unchanged. A ``request_id`` context variable is woven into
every record emitted while handling a request, which is what makes the audit
trail and latency logging in the agent traceable end-to-end.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import json as jsonlogger

from app.core.config import settings

# Correlation id for the in-flight request; set by middleware.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    """Inject the current request id into every record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = request_id_ctx.get()
        return True


def configure_logging() -> None:
    """Configure root logging once, idempotently."""
    root = logging.getLogger()
    if getattr(root, "_parcelpilot_configured", False):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
            json_ensure_ascii=False,
        )
    )

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Quiet noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root._parcelpilot_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    """Return a module logger (call :func:`configure_logging` at startup)."""
    return logging.getLogger(name)
