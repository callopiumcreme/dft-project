"""Materialized view refresh — REFRESH CONCURRENTLY requires AUTOCOMMIT engine.

Cannot run inside a transaction (PG limitation). We spin a dedicated
async engine with isolation_level='AUTOCOMMIT' for the call.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dft@db:5432/dft",
)

MVS = ("mv_mass_balance_daily", "mv_mass_balance_monthly")


async def refresh_all_mvs() -> dict[str, str]:
    """Refresh both MVs CONCURRENTLY. Returns {mv: 'ok'|error_msg}."""
    engine = create_async_engine(DATABASE_URL, isolation_level="AUTOCOMMIT", echo=False)
    results: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            for mv in MVS:
                try:
                    await conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}"))
                    results[mv] = "ok"
                except Exception as e:  # noqa: BLE001
                    logger.exception("MV refresh failed: %s", mv)
                    results[mv] = f"error: {e}"
    finally:
        await engine.dispose()
    return results
