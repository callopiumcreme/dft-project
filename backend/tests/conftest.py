"""Shared pytest fixtures for DFT backend test suite.

## Test environment

Tests connect to the local Docker PostgreSQL container directly (asyncpg).
The required env vars are read from a real ``.env`` (root of repo) via
``python-dotenv`` when available; otherwise they fall back to
``os.environ`` and finally to documented dev defaults.

Required env:

- ``DATABASE_URL``  e.g. ``postgresql+asyncpg://dft:dftdev_2026@172.22.0.2:5432/dft``
- ``JWT_SECRET``    e.g. the value in the repo ``.env``

Auth bypass:

  The FastAPI ``app`` is launched in-process via ``ASGITransport``. To avoid
  depending on the live ``admin@dft-project.com`` password — which is rotated
  per environment and **must never be reset by tests** — the
  ``_get_current_user`` dependency is overridden to return a synthetic admin
  user (and a synthetic operator user when ``role="operator"`` is requested).
  Token strings ``"test-admin-token"`` / ``"test-operator-token"`` select the
  role; any other value yields admin. Pre-existing tests that POST to
  ``/auth/login`` still work because the override only kicks in on routes that
  depend on ``_get_current_user`` — ``/auth/login`` does not.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401

# ---------------------------------------------------------------------------
# Env loading — prefer real .env via python-dotenv, fall back to os.environ
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    _REPO_ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(_REPO_ROOT / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed — fall back to plain os.environ

# DATABASE_URL: build from POSTGRES_* if the asyncpg URL isn't provided directly.
if "DATABASE_URL" not in os.environ:
    _pg_user = os.environ.get("POSTGRES_USER", "dft")
    _pg_pw = os.environ.get("POSTGRES_PASSWORD", "dftdev_2026")
    _pg_db = os.environ.get("POSTGRES_DB", "dft")
    _pg_host = os.environ.get("POSTGRES_HOST", "172.22.0.2")
    _pg_port = os.environ.get("POSTGRES_PORT", "5432")
    os.environ["DATABASE_URL"] = (
        f"postgresql+asyncpg://{_pg_user}:{_pg_pw}@{_pg_host}:{_pg_port}/{_pg_db}"
    )

os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)


# ---------------------------------------------------------------------------
# Auth dependency override — synthetic in-memory admin/operator users
# ---------------------------------------------------------------------------
def _install_auth_override() -> None:
    """Override ``_get_current_user`` so role-gated endpoints accept synthetic users.

    No real bcrypt check, no DB lookup against ``users``. The token string
    selects the role:

      - ``Authorization: Bearer test-operator-token`` → role="operator", id=2
      - everything else                                → role="admin",    id=1

    Note: ``/auth/login`` is unaffected — it doesn't depend on
    ``_get_current_user``. Tests that explicitly hit ``/auth/login`` will
    still fail if the password is wrong; the recommended pattern is to
    use the ``admin_headers`` / ``operator_headers`` fixtures below
    instead.
    """
    from app.main import app
    from app.routers.auth import _get_current_user

    class _TestUser:
        """Minimal duck-typed stand-in for ``app.models.user.User``."""

        def __init__(self, *, uid: int, role: str, email: str) -> None:
            self.id = uid
            self.role = role
            self.email = email
            self.active = True
            self.full_name = f"Test {role.title()}"
            self.password_hash = None

    from fastapi import Depends
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

    _bearer = HTTPBearer(auto_error=False)

    async def _override(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    ) -> Any:
        if credentials is None:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        token = credentials.credentials
        if token == "test-operator-token":
            return _TestUser(uid=2, role="operator", email="operator@test")
        return _TestUser(uid=1, role="admin", email="admin@test")

    app.dependency_overrides[_get_current_user] = _override


# Install at import time so any test module that imports ``app`` sees the override.
_install_auth_override()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a live AsyncSession for tests that need raw DB access."""
    async with _factory() as session:
        yield session


@pytest_asyncio.fixture
async def admin_headers() -> dict[str, str]:
    """Headers for an admin-authenticated request (auth override picks role)."""
    return {"Authorization": "Bearer test-admin-token"}


@pytest_asyncio.fixture
async def operator_headers() -> dict[str, str]:
    """Headers for an operator-authenticated request (auth override picks role)."""
    return {"Authorization": "Bearer test-operator-token"}


@pytest_asyncio.fixture
async def crown_oil_off_taker(db_session: AsyncSession) -> dict[str, object]:
    """Ensure Crown Oil UK off_taker record exists and return its row as a dict.

    Idempotent: upserts by code so the fixture is safe to call in any order
    and survives partial test-run teardown.  Caller receives:
        {"id": int, "code": "CROWN-OIL-UK", "name": "Crown Oil Ltd",
         "country": "GB", "address": "Bury, UK"}
    """
    code = "CROWN-OIL-UK"

    await db_session.execute(
        text(
            """
            INSERT INTO off_taker (code, name, country, address,
                                   created_at, updated_at)
            VALUES (:code, :name, :country, :address, NOW(), NOW())
            ON CONFLICT (code) DO UPDATE
                SET name       = EXCLUDED.name,
                    country    = EXCLUDED.country,
                    address    = EXCLUDED.address,
                    updated_at = NOW()
            """
        ),
        {
            "code": code,
            "name": "Crown Oil Ltd",
            "country": "GB",
            "address": "Bury, UK",
        },
    )
    await db_session.commit()

    row = await db_session.execute(
        text("SELECT id, code, name, country, address FROM off_taker WHERE code = :code"),
        {"code": code},
    )
    record = row.mappings().one()
    return dict(record)
