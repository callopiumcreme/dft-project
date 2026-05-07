"""QA gate — S1-11: daily_entries auth + audit_log verification (commit 880d78b)."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://dft:testonly@172.22.0.2:5432/dft")
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import get_db
from app.main import app

_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db():  # type: ignore[return]
    async with _factory() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db

ENTRY_DATE = "2026-05-07"


@pytest_asyncio.fixture
async def client() -> AsyncClient:  # type: ignore[misc]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac  # type: ignore[misc]


@pytest_asyncio.fixture
async def token(client: AsyncClient) -> str:
    resp = await client.post(
        "/auth/login",
        json={"email": "qa-test@dft.com", "password": "testpass123"},
    )
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return str(resp.json()["access_token"])


@pytest.mark.asyncio
async def test_post_without_token_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/daily-entries/", json={"entry_date": ENTRY_DATE})
    assert resp.status_code == 401, f"expected 401, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_post_with_token_returns_201_and_audit_log(
    client: AsyncClient, token: str
) -> None:
    resp = await client.post(
        "/daily-entries/",
        json={"entry_date": ENTRY_DATE, "description": "qa-test-s1-11"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["created_by"] is not None, "created_by must be set"
    entry_id = data["id"]

    async with _factory() as session:
        result = await session.execute(
            text("SELECT action, record_id, user_id FROM audit_log WHERE record_id = :rid ORDER BY id DESC LIMIT 1"),
            {"rid": entry_id},
        )
        row = result.fetchone()
    assert row is not None, "audit_log row missing"
    assert row[0] == "INSERT", f"expected action=INSERT, got {row[0]}"
    assert row[1] == entry_id
    assert row[2] is not None, "audit_log user_id must be set"


@pytest.mark.asyncio
async def test_patch_sets_updated_by(client: AsyncClient, token: str) -> None:
    # create entry first
    create_resp = await client.post(
        "/daily-entries/",
        json={"entry_date": ENTRY_DATE, "description": "patch-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    entry_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/daily-entries/{entry_id}",
        json={"description": "patched"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200, f"expected 200, got {patch_resp.status_code}: {patch_resp.text}"
    data = patch_resp.json()
    assert data["updated_by"] is not None, "updated_by must be set after PATCH"
    assert data["description"] == "patched"


@pytest.mark.asyncio
async def test_delete_soft_sets_deleted_at_and_audit(
    client: AsyncClient, token: str
) -> None:
    create_resp = await client.post(
        "/daily-entries/",
        json={"entry_date": ENTRY_DATE, "description": "delete-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    entry_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/daily-entries/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204, f"expected 204, got {del_resp.status_code}: {del_resp.text}"

    async with _factory() as session:
        result = await session.execute(
            text("SELECT deleted_at, updated_by FROM daily_entries WHERE id = :id"),
            {"id": entry_id},
        )
        row = result.fetchone()
        audit = await session.execute(
            text("SELECT action FROM audit_log WHERE record_id = :rid AND action = 'DELETE' ORDER BY id DESC LIMIT 1"),
            {"rid": entry_id},
        )
        audit_row = audit.fetchone()

    assert row is not None
    assert row[0] is not None, "deleted_at must be set (soft delete)"
    assert row[1] is not None, "updated_by must be stamped on soft delete"
    assert audit_row is not None, "audit_log DELETE row missing"
    assert audit_row[0] == "DELETE"
