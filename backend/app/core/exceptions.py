"""Typed domain exceptions.

These map cleanly onto HTTP responses in the API layer (see
``app/api/errors.py``) so the rest of the code can raise semantic errors
without knowing anything about HTTP. No stack traces or internal detail ever
leak to clients.
"""

from __future__ import annotations


class ParcelPilotError(Exception):
    """Base class for all expected, handled application errors."""

    #: Stable machine-readable code surfaced to clients & logs.
    code: str = "internal_error"
    #: Default HTTP status the API layer should use.
    http_status: int = 500

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationFailedError(ParcelPilotError):
    code = "validation_failed"
    http_status = 422


class NotFoundError(ParcelPilotError):
    code = "not_found"
    http_status = 404


class AccessDeniedError(ParcelPilotError):
    """Raised inside the repository layer when RBAC forbids the access.

    Deliberately vague to the client to avoid leaking existence of resources.
    """

    code = "access_denied"
    http_status = 403


class AuthenticationError(ParcelPilotError):
    code = "authentication_required"
    http_status = 401


class RateLimitedError(ParcelPilotError):
    code = "rate_limited"
    http_status = 429


class ToolExecutionError(ParcelPilotError):
    """A tool failed in a way the agent can reason about and recover from."""

    code = "tool_execution_failed"
    http_status = 502


class ConfirmationRequiredError(ParcelPilotError):
    """A state-changing action needs explicit user confirmation before it runs."""

    code = "confirmation_required"
    http_status = 409


class LLMError(ParcelPilotError):
    code = "llm_error"
    http_status = 502
