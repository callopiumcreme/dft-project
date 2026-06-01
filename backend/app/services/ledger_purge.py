"""Ledger tombstone purge — housekeeping for mass_balance_ledger.

`backfill_warehouse.py --reset` soft-deletes (deleted_at=NOW) the whole
live ledger before rebuilding it. Across many reruns these tombstoned
rebuild artifacts accumulate without bound. They are NOT source-of-truth
(the source tables — daily_production, byproduct_sale, consignment — stay
intact and the ledger is fully reproducible from them), so old tombstones
can be hard-deleted safely. Only rows already soft-deleted longer ago than
the retention window are removed; live rows (deleted_at IS NULL) are never
touched.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import text

from app.db.session import async_session_factory

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult

logger = logging.getLogger(__name__)

LEDGER_TOMBSTONE_RETENTION_DAYS = int(
    os.environ.get("LEDGER_TOMBSTONE_RETENTION_DAYS", "30")
)


async def purge_ledger_tombstones(retention_days: int | None = None) -> int:
    """Hard-delete mass_balance_ledger rows tombstoned > retention_days ago.

    Returns the number of rows removed. Never touches live rows.
    """
    days = LEDGER_TOMBSTONE_RETENTION_DAYS if retention_days is None else retention_days
    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "DELETE FROM mass_balance_ledger "
                "WHERE deleted_at IS NOT NULL "
                "AND deleted_at < NOW() - make_interval(days => :days)"
            ),
            {"days": days},
        )
        await db.commit()
    deleted = cast("CursorResult[Any]", result).rowcount or 0
    if deleted:
        logger.info(
            "ledger tombstone purge: removed %d rows older than %d days",
            deleted,
            days,
        )
    return deleted
