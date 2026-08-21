"""Test fixtures.

A dedicated temporary SQLite database is used so tests never touch the dev DB.
The env var is set *before* any app module is imported, so the engine binds to
the temp path. The real assessment dataset is seeded once per session.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Point the app at a throwaway DB BEFORE importing anything that builds the engine.
_TMP_DB = os.path.join(tempfile.gettempdir(), "parcelpilot_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["LLM_API_KEY"] = ""  # force offline mock

from app.core.security import Principal  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.db.seed import seed  # noqa: E402
from app.repositories.organization_repo import UserDirectory  # noqa: E402
from app.tools.base import ToolContext  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _seed_once():
    seed()
    yield


@pytest.fixture()
def session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture()
def principal_factory(session):
    def _make(email: str) -> Principal:
        ud = UserDirectory(session)
        user = ud.get_by_email(email)
        assert user is not None, f"seed user {email} missing"
        return ud.build_principal(user)

    return _make


@pytest.fixture()
def ctx_factory(session, principal_factory):
    def _make(email: str) -> ToolContext:
        return ToolContext(session, principal_factory(email), request_id="test")

    return _make
