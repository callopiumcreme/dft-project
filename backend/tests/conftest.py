"""Shared pytest fixtures for DFT backend test suite."""
from __future__ import annotations

import os

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://dft:testonly@172.22.0.2:5432/dft")
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:  # type: ignore[misc]
    """Provide a live AsyncSession for tests that need raw DB access."""
    async with _factory() as session:
        yield session  # type: ignore[misc]


@pytest_asyncio.fixture
async def crown_oil_off_taker(db_session: AsyncSession) -> dict[str, object]:
    """Ensure Crown Oil UK off_taker record exists and return its row as a dict.

    Idempotent: upserts by code so the fixture is safe to call in any order
    and survives partial test-run teardown.  Caller receives:
        {"id": int, "code": "CROWN-OIL-UK", "name": "Crown Oil Ltd",
         "country": "GB", "address": "Bury, UK"}
    """
    code = "CROWN-OIL-UK"

    # Upsert so tests are idempotent even if a previous run left a row.
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
