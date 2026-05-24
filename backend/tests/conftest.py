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

Idempotent test data:

  An autouse fixture (``_cleanup_scratch_rows``) records a baseline ``MAX(id)``
  on the scratch tables before each test, then **soft-deletes** any new rows
  matching the test-only code prefixes after the test finishes:

    - ``CONS-TEST-*``, ``CONS-VALIDATE-*``, ``CONS-ERSV-OUT-*``, ``CONS-SOFT-DELETE-*``
    - ``TEST-BUYER-*``

  Soft-delete (NOT hard-delete) preserves audit trail and respects the
  project-wide soft-delete invariant. Pos / production_link / shipment_unit
  rows have no soft-delete column; the autouse fixture hard-deletes them
  only when their parent consignment is one of the scratch consignments,
  which is consistent with the FK ON DELETE CASCADE behaviour.
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
    from app.models.user import User

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
# Scratch-row prefixes — kept in one place so all cleanup code agrees.
# ---------------------------------------------------------------------------
_SCRATCH_CONSIGNMENT_PREFIXES: tuple[str, ...] = (
    "CONS-TEST-",
    "CONS-VALIDATE-",
    "CONS-ERSV-OUT-",
    "CONS-SOFT-DELETE-",
)
_SCRATCH_OFF_TAKER_PREFIXES: tuple[str, ...] = (
    "TEST-BUYER-",
)


def _consignment_prefix_clause(column: str = "code") -> str:
    """Build a SQL ``OR``-chain matching any scratch-consignment prefix."""
    return " OR ".join(f"{column} LIKE '{p}%'" for p in _SCRATCH_CONSIGNMENT_PREFIXES)


def _off_taker_prefix_clause(column: str = "code") -> str:
    """Build a SQL ``OR``-chain matching any scratch-off_taker prefix."""
    return " OR ".join(f"{column} LIKE '{p}%'" for p in _SCRATCH_OFF_TAKER_PREFIXES)


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


# ---------------------------------------------------------------------------
# Autouse cleanup — soft-delete scratch rows created during each test.
# ---------------------------------------------------------------------------


async def _purge_scratch_rows(session: AsyncSession) -> None:
    """Soft-delete + rename-out any rows matching scratch prefixes.

    Soft-deletes the consignment / shipment_leg / off_taker rows AND rewrites
    their ``code`` to a unique tombstone (``<code>__expired_<id>``) so the
    next test run can re-use the original code without tripping the unique
    constraint. Hard-deletes the child shipment_unit / consignment_pos /
    consignment_production_link rows (no soft-delete column).

    Idempotent: matches by current code prefix, ignores already-tombstoned rows.
    """
    cons_clause = _consignment_prefix_clause("code")
    ot_clause = _off_taker_prefix_clause("code")

    # Collect scratch consignment ids (only those NOT yet tombstoned).
    cons_ids_result = await session.execute(
        text(
            f"""
            SELECT id FROM consignment
            WHERE ({cons_clause})
              AND code NOT LIKE '%__expired_%'
            """
        )
    )
    scratch_cons_ids: list[int] = [int(r[0]) for r in cons_ids_result.all()]

    if scratch_cons_ids:
        await session.execute(
            text(
                """
                DELETE FROM shipment_unit
                WHERE leg_id IN (
                    SELECT id FROM shipment_leg
                    WHERE consignment_id = ANY(:cids)
                )
                """
            ),
            {"cids": scratch_cons_ids},
        )
        await session.execute(
            text("DELETE FROM consignment_pos WHERE consignment_id = ANY(:cids)"),
            {"cids": scratch_cons_ids},
        )
        await session.execute(
            text(
                "DELETE FROM consignment_production_link "
                "WHERE consignment_id = ANY(:cids)"
            ),
            {"cids": scratch_cons_ids},
        )
        # Soft-delete shipment_leg rows (no code column, so no rename needed).
        await session.execute(
            text(
                "UPDATE shipment_leg SET deleted_at = NOW() "
                "WHERE consignment_id = ANY(:cids) "
                "  AND deleted_at IS NULL"
            ),
            {"cids": scratch_cons_ids},
        )
        # Soft-delete + tombstone-rename consignment rows so the unique
        # constraint on ``code`` is freed for the next test run.
        await session.execute(
            text(
                """
                UPDATE consignment
                SET deleted_at = COALESCE(deleted_at, NOW()),
                    code       = code || '__expired_' || id
                WHERE id = ANY(:cids)
                """
            ),
            {"cids": scratch_cons_ids},
        )

    # Same treatment for scratch off_takers.
    await session.execute(
        text(
            f"""
            UPDATE off_taker
            SET deleted_at = COALESCE(deleted_at, NOW()),
                code       = code || '__expired_' || id
            WHERE ({ot_clause})
              AND code NOT LIKE '%__expired_%'
            """
        )
    )

    await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_scratch_rows() -> AsyncIterator[None]:
    """Soft-delete + tombstone scratch rows BEFORE and AFTER each test.

    - PRE-test:  purge any leftover scratch rows from earlier runs so the
      unique constraints on ``consignment.code`` / ``off_taker.code`` are
      free for fresh inserts inside the test.
    - POST-test: purge again so the DB is clean for the next test.

    Strategy: rows matching a scratch prefix (and not already tombstoned)
    are soft-deleted AND have their code rewritten to ``<code>__expired_<id>``.
    This preserves the soft-delete audit trail (deleted_at populated, row
    still present) while making the original code available again.
    """
    async with _factory() as session:
        await _purge_scratch_rows(session)
    yield
    async with _factory() as session:
        await _purge_scratch_rows(session)
