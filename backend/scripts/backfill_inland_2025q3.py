"""Backfill script: 29 inland shipments Q3-2025 (Girardot plant → Cartagena port).

Idempotent: re-runs hit the natural-key UNIQUE
(consignment_id, container_id, load_date) WHERE deleted_at IS NULL and update
rather than duplicate. ``ersv_inland_no`` is intentionally NOT set here — it
is allocated lazily by the renderer on first GET.

Source CSV (NOT committed to repo, lives in /tmp/bl_dl/):
  /tmp/bl_dl/arrivals_containers.csv

Tables written (migration 0023_inland_shipment):
  inland_shipment — 29 rows, one per ISO container

Parent consignment row must already exist (code = 'CONS-2025-Q3-CROWN' from
0021/0022 backfills).

Usage:
    docker exec -i dft-project_backend_1 \\
        python scripts/backfill_inland_2025q3.py
"""
from __future__ import annotations

import asyncio
import csv
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)

CSV_PATH = Path("/tmp/bl_dl/arrivals_containers.csv")  # noqa: S108
CONSIGNMENT_CODE = "CONS-2025-Q3-CROWN"
ORIGIN_NODE_DEFAULT = "Girardot plant (CO)"
DESTINATION_NODE_DEFAULT = "Cartagena Contecar (CO)"


def _parse_csv_row(row: dict[str, str]) -> dict[str, object]:
    """Convert raw CSV strings into typed values for SQL bind."""
    return {
        "bl_ref": row["bl"].strip(),
        "seq_in_bl": int(row["seq"]),
        "container_id": row["container"].strip(),
        "seal_ref": row["flexitank"].strip() or None,
        "load_date": date.fromisoformat(row["load_date"]),
        "gross_kg": Decimal(row["gross_kg"]),
        "tare_kg": Decimal(row["tare_kg"]),
        "net_kg": Decimal(row["net_kg"]),
        "notes": (row.get("note") or "").strip() or None,
    }


_UPSERT_SQL = text(
    """
    INSERT INTO inland_shipment (
        consignment_id, bl_ref, seq_in_bl, container_id, seal_ref,
        load_date, gross_kg, tare_kg, net_kg, notes,
        origin_node, destination_node
    )
    VALUES (
        :consignment_id, :bl_ref, :seq_in_bl, :container_id, :seal_ref,
        :load_date, :gross_kg, :tare_kg, :net_kg, :notes,
        :origin_node, :destination_node
    )
    ON CONFLICT (consignment_id, container_id, load_date)
        WHERE deleted_at IS NULL
        DO UPDATE SET
            bl_ref = EXCLUDED.bl_ref,
            seq_in_bl = EXCLUDED.seq_in_bl,
            seal_ref = EXCLUDED.seal_ref,
            gross_kg = EXCLUDED.gross_kg,
            tare_kg = EXCLUDED.tare_kg,
            net_kg = EXCLUDED.net_kg,
            notes = COALESCE(EXCLUDED.notes, inland_shipment.notes),
            updated_at = NOW()
    RETURNING id, (xmax = 0) AS inserted
    """
)


async def _backfill(db: AsyncSession) -> tuple[int, int]:
    """Run upsert for every CSV row. Returns (inserted, updated)."""
    cons_id_result = await db.execute(
        text(
            "SELECT id FROM consignment WHERE code = :code AND deleted_at IS NULL"
        ),
        {"code": CONSIGNMENT_CODE},
    )
    consignment_id = cons_id_result.scalar_one_or_none()
    if consignment_id is None:
        print(
            f"ERROR: consignment '{CONSIGNMENT_CODE}' not found. "
            "Run backfill_consignment_2025q3.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}.", file=sys.stderr)
        sys.exit(1)

    inserted = 0
    updated = 0
    with CSV_PATH.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            parsed = _parse_csv_row(row)
            result = await db.execute(
                _UPSERT_SQL,
                {
                    "consignment_id": consignment_id,
                    "origin_node": ORIGIN_NODE_DEFAULT,
                    "destination_node": DESTINATION_NODE_DEFAULT,
                    **parsed,
                },
            )
            ret = result.mappings().one()
            if ret["inserted"]:
                inserted += 1
            else:
                updated += 1

    await db.commit()
    return inserted, updated


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as db:
        inserted, updated = await _backfill(db)

    await engine.dispose()
    total = inserted + updated
    print(
        f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] inland backfill done: "
        f"{total} rows ({inserted} inserted, {updated} updated)."
    )


if __name__ == "__main__":
    asyncio.run(main())
