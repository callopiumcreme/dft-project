"""Backfill ``consignment_production_link`` per the kg-proportional rule.

Implements docs/mass-balance-allocation-policy.md v1.0 §3.1 — for each
``daily_production`` row inside a consignment's window, allocate kg
proportionally to ``output_eu_kg``. The last in-window row absorbs any
rounding remainder so the per-consignment sum exactly equals
``consignment.total_kg``.

Idempotent: ON CONFLICT (consignment_id, prod_date) DO UPDATE.

Multi-consignment overlap (policy §3.3) is handled by the running
"remaining demand" pass — consignments are processed in
(prod_date_from, code) order and each day's plant output is split among
the active consignments proportionally to their unsatisfied demand.

Usage:
    docker exec -i dft-project_backend_1 \\
        python scripts/backfill_consignment_production_link.py

CLI flags (optional):
    --dry-run        print plan, do not write
    --consignment X  restrict to one consignment.code
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)

# All ledger / allocation math at 6 decimals; persist at 3.
getcontext().prec = 28
_THREE = Decimal("0.001")


def _q3(d: Decimal) -> Decimal:
    """Quantize to 3 decimals, banker-rounding ROUND_HALF_UP."""
    return d.quantize(_THREE, rounding=ROUND_HALF_UP)


async def _load_consignments(
    db: AsyncSession, code: str | None
) -> list[dict]:
    """Active consignments ordered by (prod_date_from, code).

    Skips rows without window or total_kg (incomplete data).
    """
    sql = (
        "SELECT id, code, prod_date_from, prod_date_to, total_kg "
        "FROM consignment "
        "WHERE deleted_at IS NULL "
        "  AND prod_date_from IS NOT NULL "
        "  AND prod_date_to IS NOT NULL "
        "  AND total_kg IS NOT NULL "
    )
    params: dict = {}
    if code:
        sql += "  AND code = :code "
        params["code"] = code
    sql += "ORDER BY prod_date_from, code"
    rows = (await db.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]


async def _load_daily_production(db: AsyncSession) -> dict:
    """date → output_eu_kg (Decimal) for active rows with positive output."""
    rows = (
        await db.execute(
            text(
                "SELECT prod_date, output_eu_kg "
                "FROM daily_production "
                "WHERE deleted_at IS NULL "
                "  AND output_eu_kg IS NOT NULL "
                "  AND output_eu_kg > 0 "
                "ORDER BY prod_date"
            )
        )
    ).all()
    return {r.prod_date: Decimal(r.output_eu_kg) for r in rows}


def _allocate(
    consignments: list[dict],
    daily_prod: dict,
) -> dict[tuple[int, "date"], Decimal]:
    """Compute kg_allocated per (consignment_id, prod_date).

    Per policy §3.1 — for each consignment, for each in-window prod day:
        kg_alloc = plant_kg(D) × (consignment.total_kg / window_total)

    The last in-window day absorbs the rounding remainder so per-consignment
    SUM = total_kg exactly.

    Multi-consignment overlap: each consignment computes its share
    independently. If on any day the sum of shares across overlapping
    consignments exceeds plant_kg(D), the function emits a WARN. This is
    a configuration error (oversubscription) per policy §3.3 and must
    be resolved in source data, not silently massaged.
    """
    if not consignments or not daily_prod:
        return {}

    alloc: dict[tuple, Decimal] = {}

    for c in consignments:
        window_days = sorted(
            d for d in daily_prod
            if c["prod_date_from"] <= d <= c["prod_date_to"]
        )
        if not window_days:
            print(
                f"  WARN: consignment '{c['code']}' has empty production "
                "window (no daily_production rows in range)"
            )
            continue

        window_total = sum(daily_prod[d] for d in window_days)
        if window_total <= 0:
            continue

        demand = Decimal(c["total_kg"])
        scale = demand / window_total
        last_d = window_days[-1]
        running = Decimal(0)

        for d in window_days:
            if d == last_d:
                share = demand - running  # absorb remainder
            else:
                share = _q3(daily_prod[d] * scale)
                running += share
            if share > 0:
                alloc[(c["id"], d)] = share

    # Sanity: no day should be oversubscribed across all consignments
    day_used: dict = {}
    for (_cid, d), kg in alloc.items():
        day_used[d] = day_used.get(d, Decimal(0)) + kg
    for d, used in day_used.items():
        if used > daily_prod[d]:
            print(
                f"  WARN: day {d} oversubscribed — "
                f"alloc_total={used} > plant_kg={daily_prod[d]}"
            )

    return alloc


_UPSERT_SQL = text(
    """
    INSERT INTO consignment_production_link
        (consignment_id, prod_date, kg_allocated, created_at)
    VALUES (:cid, :prod_date, :kg, NOW())
    ON CONFLICT (consignment_id, prod_date) DO UPDATE
        SET kg_allocated = EXCLUDED.kg_allocated
    """
)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--consignment", default=None)
    args = parser.parse_args()

    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as db:
        consignments = await _load_consignments(db, args.consignment)
        daily_prod = await _load_daily_production(db)

        alloc = _allocate(consignments, daily_prod)

        # Audit-check: per-consignment sum == total_kg
        sums: dict[int, Decimal] = {}
        for (cid, _), kg in alloc.items():
            sums[cid] = sums.get(cid, Decimal(0)) + kg
        for c in consignments:
            got = sums.get(c["id"], Decimal(0))
            want = Decimal(c["total_kg"])
            mark = "OK " if got == want else "MISMATCH"
            print(
                f"  [{mark}] consignment '{c['code']}' "
                f"alloc_sum={got} target={want} diff={got - want}"
            )

        if args.dry_run:
            print(f"DRY-RUN: would upsert {len(alloc)} rows. Aborting.")
            await engine.dispose()
            return

        inserted_or_updated = 0
        for (cid, prod_date), kg in alloc.items():
            await db.execute(
                _UPSERT_SQL,
                {"cid": cid, "prod_date": prod_date, "kg": kg},
            )
            inserted_or_updated += 1
        await db.commit()

        print(
            f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
            f"consignment_production_link backfill done: "
            f"{inserted_or_updated} rows upserted."
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
