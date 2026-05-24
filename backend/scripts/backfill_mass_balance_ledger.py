"""Backfill ``mass_balance_ledger`` from existing source tables.

Builds the canonical append-only ledger per
docs/mass-balance-allocation-policy.md v1.0 from rows already in:

  daily_inputs                 → event_type='inbound'
  daily_production             → event_type='production'
  consignment_production_link  → event_type='consign_assign'
  inland_shipment              → event_type='inland_dispatch'
  shipment_leg (bl_ocean)      → event_type='bl_load'
  shipment_leg (utb_transload) → event_type='utb_transload'
  consignment_pos              → event_type='pos_issue'
  shipment_leg (delivery_uk)   → event_type='uk_delivery'

Idempotent: ON CONFLICT (ref_table, ref_id, event_type, event_date) DO UPDATE.

Running plant-stock balance is recomputed in chronological order across
(inbound, production, consign_assign) events. inland_dispatch / bl_load /
utb_transload / pos_issue / uk_delivery events do NOT touch the plant
stock balance — they are downstream-of-allocation accounting (the kg are
already committed to the consignment).

Usage:
    docker exec -i dft-project_backend_1 \\
        python scripts/backfill_mass_balance_ledger.py [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime
from decimal import Decimal
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


_UPSERT_SQL = text(
    """
    INSERT INTO mass_balance_ledger (
        event_type, event_date, kg_in, kg_out,
        ref_table, ref_id, ref_doc_no, consignment_id,
        prev_balance_kg, post_balance_kg, notes
    )
    VALUES (
        :event_type, :event_date, :kg_in, :kg_out,
        :ref_table, :ref_id, :ref_doc_no, :consignment_id,
        :prev_balance_kg, :post_balance_kg, :notes
    )
    ON CONFLICT (ref_table, ref_id, event_type, event_date)
        WHERE deleted_at IS NULL
        DO UPDATE SET
            kg_in            = EXCLUDED.kg_in,
            kg_out           = EXCLUDED.kg_out,
            ref_doc_no       = EXCLUDED.ref_doc_no,
            consignment_id   = EXCLUDED.consignment_id,
            prev_balance_kg  = EXCLUDED.prev_balance_kg,
            post_balance_kg  = EXCLUDED.post_balance_kg,
            notes            = COALESCE(EXCLUDED.notes, mass_balance_ledger.notes)
    RETURNING id, (xmax = 0) AS inserted
    """
)


async def _collect_events(db: AsyncSession) -> list[dict]:
    """Build all ledger events in chronological order.

    Returns a list of dicts ready for the upsert SQL. ``prev_balance_kg``
    and ``post_balance_kg`` are recomputed in a second pass once events
    are sorted, because the plant-stock balance is path-dependent.
    """
    events: list[dict] = []

    # --- 1. inbound (daily_inputs) -----------------------------------------
    rows = (await db.execute(text(
        "SELECT id, entry_date, total_input_kg, ersv_number "
        "FROM daily_inputs WHERE deleted_at IS NULL "
        "  AND total_input_kg > 0 "
        "ORDER BY entry_date, id"
    ))).all()
    for r in rows:
        events.append({
            "event_type": "inbound",
            "event_date": r.entry_date,
            "kg_in": Decimal(r.total_input_kg),
            "kg_out": None,
            "ref_table": "daily_inputs",
            "ref_id": r.id,
            "ref_doc_no": r.ersv_number,
            "consignment_id": None,
            "notes": "ELT feedstock credit to plant mass-balance",
        })

    # --- 2. production (daily_production) ---------------------------------
    rows = (await db.execute(text(
        "SELECT id, prod_date, output_eu_kg "
        "FROM daily_production WHERE deleted_at IS NULL "
        "  AND output_eu_kg IS NOT NULL AND output_eu_kg > 0 "
        "ORDER BY prod_date, id"
    ))).all()
    for r in rows:
        events.append({
            "event_type": "production",
            "event_date": r.prod_date,
            "kg_in": Decimal(r.output_eu_kg),
            "kg_out": None,
            "ref_table": "daily_production",
            "ref_id": r.id,
            "ref_doc_no": None,
            "consignment_id": None,
            "notes": "DEV-P100 EU-certified output credited to plant stock",
        })

    # --- 3. consign_assign (consignment_production_link) ------------------
    rows = (await db.execute(text(
        "SELECT consignment_id, prod_date, kg_allocated "
        "FROM consignment_production_link "
        "ORDER BY prod_date, consignment_id"
    ))).all()
    for r in rows:
        events.append({
            "event_type": "consign_assign",
            "event_date": r.prod_date,
            "kg_in": None,
            "kg_out": Decimal(r.kg_allocated),
            "ref_table": "consignment_production_link",
            "ref_id": r.consignment_id,
            "ref_doc_no": None,
            "consignment_id": r.consignment_id,
            "notes": "kg debited from plant stock, assigned to consignment",
        })

    # --- 4. inland_dispatch (inland_shipment) -----------------------------
    rows = (await db.execute(text(
        "SELECT id, consignment_id, load_date, net_kg, ersv_inland_no, "
        "       container_id "
        "FROM inland_shipment WHERE deleted_at IS NULL "
        "ORDER BY load_date, id"
    ))).all()
    for r in rows:
        events.append({
            "event_type": "inland_dispatch",
            "event_date": r.load_date,
            "kg_in": None,
            "kg_out": Decimal(r.net_kg),
            "ref_table": "inland_shipment",
            "ref_id": r.id,
            "ref_doc_no": r.ersv_inland_no,
            "consignment_id": r.consignment_id,
            "notes": f"container {r.container_id} dispatched plant→port",
        })

    # --- 5/6/8. shipment_leg events ---------------------------------------
    rows = (await db.execute(text(
        "SELECT id, consignment_id, seq, leg_type, document_ref, "
        "       document_date, kg_in, kg_out, kg_stock_residual "
        "FROM shipment_leg WHERE deleted_at IS NULL "
        "ORDER BY consignment_id, seq"
    ))).all()
    for r in rows:
        if r.leg_type == "bl_ocean":
            evt = "bl_load"
            kgi = Decimal(r.kg_in)
            kgo = None
            note = "ocean BL loaded at Cartagena Contecar"
        elif r.leg_type == "utb_transload":
            evt = "utb_transload"
            kgi = Decimal(r.kg_in)
            kgo = Decimal(r.kg_out)
            note = (
                f"UTB transload Rotterdam — in={r.kg_in} out={r.kg_out} "
                f"residual={r.kg_stock_residual}"
            )
        elif r.leg_type == "delivery_uk":
            evt = "uk_delivery"
            kgi = None
            kgo = Decimal(r.kg_out)
            note = "delivery UK Crown Oil"
        else:
            # plant_to_port / port_loading / nl_to_uk_export — skip (not in
            # current data; add later if/when present)
            continue
        events.append({
            "event_type": evt,
            "event_date": r.document_date or date.today(),
            "kg_in": kgi,
            "kg_out": kgo,
            "ref_table": "shipment_leg",
            "ref_id": r.id,
            "ref_doc_no": r.document_ref,
            "consignment_id": r.consignment_id,
            "notes": note,
        })

    # --- 7. pos_issue (consignment_pos) -----------------------------------
    # consignment_pos has composite PK (consignment_id, pos_number).
    # Use consignment_id as ref_id; event_date column disambiguates per PoS.
    # That works only if at most one PoS per consignment per date — true in
    # current Q3 data (PoS dates spread across delivery_uk JLY001..JLY020).
    # If that invariant breaks, switch ref_id to a synthetic surrogate.
    rows = (await db.execute(text(
        "SELECT consignment_id, pos_number, kg_net, ersv_outbound_no, "
        "       created_at "
        "FROM consignment_pos WHERE deleted_at IS NULL "
        "ORDER BY consignment_id, pos_number"
    ))).all()
    # For PoS, use created_at::date as event_date for ordering; for
    # uniqueness we still rely on (ref_table, ref_id, event_type,
    # event_date) — so multiple PoS on same date won't collide because
    # we synthesise a unique ref_id by hashing pos_number.
    for r in rows:
        # Stable integer ref_id from pos_number (audit-friendly: numeric
        # portion of OISCRO-NNNN-25 = NNNN, scoped per-consignment).
        pos_digits = "".join(ch for ch in r.pos_number if ch.isdigit())
        ref_id = int(pos_digits) if pos_digits else r.consignment_id
        events.append({
            "event_type": "pos_issue",
            "event_date": (
                r.created_at.date() if r.created_at else date.today()
            ),
            "kg_in": None,
            "kg_out": Decimal(r.kg_net) if r.kg_net is not None else None,
            "ref_table": "consignment_pos",
            "ref_id": ref_id,
            "ref_doc_no": r.pos_number,
            "consignment_id": r.consignment_id,
            "notes": (
                f"PoS {r.pos_number} issued"
                + (
                    f"; outbound eRSV {r.ersv_outbound_no}"
                    if r.ersv_outbound_no else ""
                )
            ),
        })

    return events


def _compute_balances(events: list[dict]) -> None:
    """Walk events in chronological order; fill prev/post plant balance.

    Plant stock only moves on inbound / production / consign_assign.
    Other events leave balance unchanged but still inherit the running
    balance so audit packs show the contemporaneous stock level.
    """
    # Stable sort: by event_date, then by event_type priority (inbound
    # before production before consign_assign on same day = lifecycle
    # order), then by ref_id for determinism.
    type_order = {
        "inbound": 0,
        "production": 1,
        "consign_assign": 2,
        "inland_dispatch": 3,
        "bl_load": 4,
        "utb_transload": 5,
        "pos_issue": 6,
        "uk_delivery": 7,
        "correction": 99,
    }
    events.sort(key=lambda e: (
        e["event_date"], type_order.get(e["event_type"], 50), e["ref_id"]
    ))

    balance = Decimal(0)
    for ev in events:
        ev["prev_balance_kg"] = balance
        if ev["event_type"] in ("inbound", "production"):
            balance += ev["kg_in"] or Decimal(0)
        elif ev["event_type"] == "consign_assign":
            # kg leaves plant feedstock/product pool into consignment account
            balance -= ev["kg_out"] or Decimal(0)
        # downstream events (inland_dispatch etc.) don't move plant stock
        ev["post_balance_kg"] = balance


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as db:
        events = await _collect_events(db)

    _compute_balances(events)

    # Summarise by event_type
    summary: dict[str, int] = {}
    for ev in events:
        summary[ev["event_type"]] = summary.get(ev["event_type"], 0) + 1
    print("  Event-type counts (pre-upsert):")
    for t, n in sorted(summary.items()):
        print(f"    {t:18s} {n}")

    if args.dry_run:
        print(f"DRY-RUN: would upsert {len(events)} rows. Aborting.")
        await engine.dispose()
        return

    async with sm() as db:
        inserted = 0
        updated = 0
        for ev in events:
            r = await db.execute(_UPSERT_SQL, ev)
            row = r.mappings().one()
            if row["inserted"]:
                inserted += 1
            else:
                updated += 1
        await db.commit()

    await engine.dispose()
    print(
        f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
        f"mass_balance_ledger backfill done: {len(events)} rows "
        f"({inserted} inserted, {updated} updated)."
    )


if __name__ == "__main__":
    asyncio.run(main())
