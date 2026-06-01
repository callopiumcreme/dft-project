"""Backfill ``mass_balance_ledger`` for the warehouse / per-product view.

Extends the canonical mass-balance ledger (migration 0024) with the
per-``product_kind`` event streams introduced in migration 0026
(opening, byproduct_sale, syngas_burn, h2o_vent). Builds running
per-product balances so ``v_warehouse_stock`` and
``v_warehouse_recent_movements`` light up immediately after a fresh
``alembic upgrade head`` on a clean environment.

Event sources (chronological):

  1. opening              — six manual opening rows @ 2024-12-31 from
                            physical stocktake (eu_oil, plus_oil,
                            carbon_black, metal_scrap, syngas=0, h2o=0)
  2. daily_production     → production events per product_kind:
                              eu_prod_kg     → product_kind=eu_oil
                              plus_prod_kg   → product_kind=plus_oil
                              carbon_black_kg→ product_kind=carbon_black
                              metal_scrap_kg → product_kind=metal_scrap
                              gas_syngas_kg  → product_kind=syngas
                                               + same-day syngas_burn (kg_out)
                              h2o_kg         → product_kind=h2o
                                               + same-day h2o_vent (kg_out)
  3. consignment          → uk_delivery (kg_out) on terminal status
                            + consign_assign (informational, 0/0) on
                            in-flight statuses. The trigger that
                            actually debits stock is controlled by the
                            ``DISCHARGE_TRIGGER`` constant below.
  4. byproduct_sale       → byproduct_sale (kg_out) per product_kind

Per-product running balances are recomputed in chronological order
across all events so ``prev_balance_kg`` / ``post_balance_kg`` reflect
the on-hand kg per product_kind contemporaneously with the row.

Idempotency:
  - ``--reset``  truncates ``mass_balance_ledger`` first (CASCADE-safe
                 because ``corrects_id`` is the only self-FK and we
                 DELETE rather than TRUNCATE, so RESTRICT is honoured
                 by ordering: rows have no corrects_id in backfill).
  - Otherwise we upsert ON CONFLICT
                 (ref_table, ref_id, event_type, event_date) so the
                 script is safe to re-run.

Quantity arithmetic is Decimal end-to-end — NUMERIC(14,3) columns must
never round-trip through float.

Usage:
    docker exec -i dft-project_backend_1 \\
        python scripts/backfill_warehouse.py [--dry-run] [--reset] \\
        [--from-date 2024-12-31]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402, TC002 — used in runtime annotations

from app.db.session import async_session_factory  # noqa: E402

# ----------------------------------------------------------------------
# Configuration constants
# ----------------------------------------------------------------------

# Which consignment status triggers the actual stock debit on eu_oil.
# Alternatives:
#   'delivered_uk' — debit when goods physically arrive in UK (current default)
#   'pos_issue'    — debit when PoS document is issued
#   'bl_load'      — debit at ocean BL load (Cartagena Contecar)
# Changing this only affects which consignment events emit kg_out; the
# informational consign_assign rows are always written for traceability.
DISCHARGE_TRIGGER = "pos_issue"

# Opening physical stock @ 2024-12-31. Hardcoded from physical
# stocktake — the only place in the codebase that asserts these values.
_OPENING_DEFAULT_DATE = date(2024, 12, 31)
_OPENING_BALANCES: dict[str, Decimal] = {
    "eu_oil":       Decimal("2475623"),
    "plus_oil":     Decimal("2972349"),
    "carbon_black": Decimal("1569832"),
    "metal_scrap":  Decimal("993920"),
    "syngas":       Decimal("0"),
    "h2o":          Decimal("0"),
}

# Commercial product_kind (byproduct_sale) → physical ledger code. The
# ledger CHECK only knows physical streams; dev_p200 is the commercial name
# of the plus_oil byproduct sold to Conquer.
_LEDGER_KIND = {"dev_p200": "plus_oil"}

# Statuses that count as "delivered" — these get a uk_delivery (kg_out) row.
_TERMINAL_STATUSES = {"delivered_uk", "closed"}

# Statuses that count as "in-flight" — these get an informational
# consign_assign row (kg_in=0, kg_out=0) so the UI can show "reserved".
_IN_FLIGHT_STATUSES = {"loaded", "in_transit", "at_utb"}

# Stable ordering of events on the same date so the running balance is
# deterministic. Opening must come first (sets the baseline). Production
# credits before any debits so we never momentarily go negative.
_TYPE_ORDER = {
    "opening":         0,
    "inbound":         1,
    "production":      2,
    "syngas_burn":     3,
    "h2o_vent":        3,
    "consign_assign":  4,
    "inland_dispatch": 5,
    "bl_load":         6,
    "utb_transload":   7,
    "pos_issue":       8,
    "uk_delivery":     9,
    "byproduct_sale":  10,
    "correction":      99,
}


_UPSERT_SQL = text(
    """
    INSERT INTO mass_balance_ledger (
        event_type, event_date, product_kind,
        kg_in, kg_out,
        ref_table, ref_id, ref_doc_no, consignment_id,
        prev_balance_kg, post_balance_kg, notes
    )
    VALUES (
        :event_type, :event_date, :product_kind,
        :kg_in, :kg_out,
        :ref_table, :ref_id, :ref_doc_no, :consignment_id,
        :prev_balance_kg, :post_balance_kg, :notes
    )
    ON CONFLICT (ref_table, ref_id, event_type, event_date)
        WHERE deleted_at IS NULL
        DO UPDATE SET
            product_kind     = EXCLUDED.product_kind,
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


# ----------------------------------------------------------------------
# Event collectors
# ----------------------------------------------------------------------


def _opening_events(opening_date: date) -> list[dict]:
    """Six opening rows — one per product_kind — fixing the baseline.

    ``ref_id`` is the row's index in ``_OPENING_BALANCES`` so we have a
    stable natural key that doesn't collide across products. ``ref_table
    = 'manual'`` makes it explicit in audit dumps that no source row
    backs these values — only the physical stocktake.
    """
    events: list[dict] = []
    for idx, (kind, kg) in enumerate(_OPENING_BALANCES.items(), start=1):
        events.append({
            "event_type": "opening",
            "event_date": opening_date,
            "product_kind": kind,
            "kg_in": kg,
            "kg_out": Decimal(0),
            "ref_table": "manual",
            "ref_id": idx,
            "ref_doc_no": None,
            "consignment_id": None,
            "notes": (
                f"Opening balance {opening_date.isoformat()} "
                "from physical stocktake"
            ),
        })
    return events


async def _production_events(
    db: AsyncSession, from_date: date
) -> list[dict]:
    """Replay daily_production rows into per-product_kind events.

    Each non-zero column on a daily_production row becomes one (or, for
    syngas / h2o, two) ledger rows. We use the row's primary key as
    ``ref_id`` so the natural key (ref_table, ref_id, event_type,
    event_date) is unique per product_kind (event_type embeds it).
    """
    rows = (await db.execute(text(
        "SELECT id, prod_date, "
        "       eu_prod_kg, plus_prod_kg, "
        "       carbon_black_kg, metal_scrap_kg, "
        "       gas_syngas_kg, h2o_kg "
        "FROM daily_production "
        "WHERE deleted_at IS NULL "
        "  AND prod_date > :from_date "
        "ORDER BY prod_date, id"
    ), {"from_date": from_date})).all()

    events: list[dict] = []

    def _qty(value: Decimal | int | None) -> Decimal:
        return Decimal(value) if value is not None else Decimal(0)

    # Column → product_kind mapping for the simple credit-only streams.
    _SIMPLE_KINDS: tuple[tuple[str, str], ...] = (
        ("eu_prod_kg",       "eu_oil"),
        ("plus_prod_kg",     "plus_oil"),
        ("carbon_black_kg",  "carbon_black"),
        ("metal_scrap_kg",   "metal_scrap"),
    )

    for r in rows:
        # eu_oil / plus_oil / carbon_black / metal_scrap
        for col, kind in _SIMPLE_KINDS:
            kg = _qty(getattr(r, col))
            if kg > 0:
                events.append({
                    "event_type": "production",
                    "event_date": r.prod_date,
                    "product_kind": kind,
                    "kg_in": kg,
                    "kg_out": None,
                    "ref_table": "daily_production",
                    # ref_id embeds product_kind so 4 rows from same
                    # source row don't collide on the natural key.
                    # We multiply by 10 and add a per-kind offset.
                    "ref_id": r.id * 10 + _SIMPLE_KINDS.index(
                        (col, kind)
                    ),
                    "ref_doc_no": None,
                    "consignment_id": None,
                    "notes": (
                        f"{kind} produced on {r.prod_date.isoformat()}"
                    ),
                })

        # syngas: produced and immediately burned same day → net zero
        syngas_kg = _qty(r.gas_syngas_kg)
        if syngas_kg > 0:
            events.append({
                "event_type": "production",
                "event_date": r.prod_date,
                "product_kind": "syngas",
                "kg_in": syngas_kg,
                "kg_out": None,
                "ref_table": "daily_production",
                "ref_id": r.id * 10 + 4,
                "ref_doc_no": None,
                "consignment_id": None,
                "notes": "syngas produced (combusted in-process)",
            })
            events.append({
                "event_type": "syngas_burn",
                "event_date": r.prod_date,
                "product_kind": "syngas",
                "kg_in": None,
                "kg_out": syngas_kg,
                "ref_table": "daily_production",
                "ref_id": r.id * 10 + 4,
                "ref_doc_no": None,
                "consignment_id": None,
                "notes": "syngas burned for process heat (zero net stock)",
            })

        # h2o: produced and vented same day → net zero
        h2o_kg = _qty(r.h2o_kg)
        if h2o_kg > 0:
            events.append({
                "event_type": "production",
                "event_date": r.prod_date,
                "product_kind": "h2o",
                "kg_in": h2o_kg,
                "kg_out": None,
                "ref_table": "daily_production",
                "ref_id": r.id * 10 + 5,
                "ref_doc_no": None,
                "consignment_id": None,
                "notes": "process water condensate captured",
            })
            events.append({
                "event_type": "h2o_vent",
                "event_date": r.prod_date,
                "product_kind": "h2o",
                "kg_in": None,
                "kg_out": h2o_kg,
                "ref_table": "daily_production",
                "ref_id": r.id * 10 + 5,
                "ref_doc_no": None,
                "consignment_id": None,
                "notes": "process water vented (zero net stock)",
            })

    return events


async def _consignment_events(
    db: AsyncSession, from_date: date
) -> list[dict]:
    """Replay consignment outbound flow per DISCHARGE_TRIGGER='pos_issue'.

    Policy: the EU oil debit happens at the moment the PoS document is
    legally issued (``consignment_pos.issuance_date``), not at physical
    UK arrival. For each consignment we therefore emit:

      * one ``pos_issue`` row per ``consignment_pos`` with an
        ``issuance_date`` populated (kg_out = cp.kg_net, event_date =
        cp.issuance_date) — these are the actual stock debits;
      * one informational ``consign_assign`` row (kg_in=0, kg_out=0)
        carrying the RESERVED kg figure = total_kg - sum(POS-issued kg)
        so the UI can render "available = stock - reserved" without
        re-deriving from sources.

    The legacy ``uk_delivery`` row is no longer emitted while
    DISCHARGE_TRIGGER='pos_issue'. It can be re-enabled by flipping the
    constant + restoring the branch — kept as a no-op for now so the
    intent is visible in diffs.
    """
    rows = (await db.execute(text(
        "SELECT id, code, status, total_kg, "
        "       prod_date_from, prod_date_to, "
        "       ersv_outbound_no "
        "FROM consignment "
        "WHERE deleted_at IS NULL "
        "  AND prod_date_to IS NOT NULL "
        "  AND prod_date_to > :from_date "
        "ORDER BY prod_date_to, id"
    ), {"from_date": from_date})).all()

    events: list[dict] = []

    for r in rows:
        if r.total_kg is None:
            continue
        total_kg = Decimal(r.total_kg)
        # NB: 'delivered_at' not yet on the schema; use prod_date_to as
        # the consign_assign event_date proxy.
        event_date = r.prod_date_to or date.today()

        # POS-issuance events: one row per consignment_pos with an
        # issuance_date populated. kg_out = pos.kg_net, event_date =
        # pos.issuance_date. ref_table='consignment_pos' so the ledger
        # row uniquely identifies the PoS document.
        pos_rows = (await db.execute(text(
            "SELECT pos_number, kg_net, issuance_date "
            "FROM consignment_pos "
            "WHERE consignment_id = :cid "
            "  AND deleted_at IS NULL "
            "  AND issuance_date IS NOT NULL "
            "ORDER BY issuance_date, pos_number"
        ), {"cid": r.id})).all()

        pos_issued_kg = Decimal(0)
        for cp in pos_rows:
            if cp.kg_net is None:
                continue
            kg = Decimal(cp.kg_net)
            pos_issued_kg += kg
            # Stable synthetic ref_id: hash on (consignment_id, pos_number)
            # via a positive deterministic integer; the (ref_table, ref_id,
            # event_type, event_date) unique key still applies. Using the
            # consignment.id * 1_000_000 + ordinal so re-runs are stable.
            events.append({
                "event_type": "pos_issue",
                "event_date": cp.issuance_date,
                "product_kind": "eu_oil",
                "kg_in": None,
                "kg_out": kg,
                "ref_table": "consignment_pos",
                "ref_id": r.id * 1_000_000 + int(cp.pos_number.split("-")[1]),
                "ref_doc_no": cp.pos_number,
                "consignment_id": r.id,
                "notes": (
                    f"POS issued — {cp.pos_number} (consignment {r.code})"
                ),
            })

        # Reserved residual = total_kg - POS-issued kg. Emitted as an
        # informational consign_assign row when > 0 so the UI subtracts
        # it from stock_kg to compute "available".
        reserved_kg = total_kg - pos_issued_kg
        if reserved_kg > 0 and r.status in (
            _IN_FLIGHT_STATUSES | _TERMINAL_STATUSES
        ):
            # Informational — stock not yet debited; UI subtracts
            # reserved kg from stock for "available" view.
            events.append({
                "event_type": "consign_assign",
                "event_date": event_date,
                "product_kind": "eu_oil",
                "kg_in": Decimal(0),
                "kg_out": Decimal(0),
                "ref_table": "consignment",
                "ref_id": r.id,
                "ref_doc_no": r.code,
                "consignment_id": r.id,
                "notes": (
                    f"reserved kg={reserved_kg} (status={r.status}, "
                    f"total={total_kg}, pos_issued={pos_issued_kg}); "
                    "informational only — stock available view "
                    "subtracts reserved kg"
                ),
            })

    return events


async def _byproduct_sale_events(
    db: AsyncSession, from_date: date
) -> list[dict]:
    """Replay byproduct_sale rows → byproduct_sale event rows.

    byproduct_sale.product_kind carries the commercial code (e.g. dev_p200);
    the ledger CHECK only knows physical codes, so map commercial→physical
    via _LEDGER_KIND before writing the balance event. dev_p200 is the
    commercial name of the plus_oil physical stream sold to Conquer.
    """
    rows = (await db.execute(text(
        "SELECT id, product_kind, sale_date, kg_net, "
        "       invoice_no, buyer_id "
        "FROM byproduct_sale "
        "WHERE deleted_at IS NULL "
        "  AND sale_date > :from_date "
        "ORDER BY sale_date, id"
    ), {"from_date": from_date})).all()

    events: list[dict] = []
    for r in rows:
        ledger_kind = _LEDGER_KIND.get(r.product_kind, r.product_kind)
        events.append({
            "event_type": "byproduct_sale",
            "event_date": r.sale_date,
            "product_kind": ledger_kind,
            "kg_in": None,
            "kg_out": Decimal(r.kg_net),
            "ref_table": "byproduct_sale",
            "ref_id": r.id,
            "ref_doc_no": r.invoice_no,
            "consignment_id": None,
            "notes": (
                f"{r.product_kind} sale to buyer_id={r.buyer_id}"
                + (f", invoice {r.invoice_no}" if r.invoice_no else "")
            ),
        })
    return events


# ----------------------------------------------------------------------
# Balance computation
# ----------------------------------------------------------------------


def _compute_balances(events: list[dict]) -> None:
    """Walk events in chronological order; fill prev/post per product_kind.

    Each product_kind has its own running balance — events on one kind
    do not affect another kind's balance. Stable sort by
    (event_date, type_order, ref_id) so the walk is deterministic.
    """
    events.sort(key=lambda e: (
        e["event_date"],
        _TYPE_ORDER.get(e["event_type"], 50),
        e["product_kind"],
        e["ref_id"],
    ))

    balances: dict[str, Decimal] = {}
    for ev in events:
        kind = ev["product_kind"]
        balance = balances.get(kind, Decimal(0))
        ev["prev_balance_kg"] = balance
        balance += ev["kg_in"] or Decimal(0)
        balance -= ev["kg_out"] or Decimal(0)
        ev["post_balance_kg"] = balance
        balances[kind] = balance


# ----------------------------------------------------------------------
# Idempotency helpers
# ----------------------------------------------------------------------


async def _opening_already_present(
    db: AsyncSession, opening_date: date
) -> set[str]:
    """Return set of product_kind values that already have an opening row."""
    rows = (await db.execute(text(
        "SELECT product_kind FROM mass_balance_ledger "
        "WHERE event_type = 'opening' "
        "  AND event_date = :d "
        "  AND deleted_at IS NULL"
    ), {"d": opening_date})).all()
    return {r.product_kind for r in rows}


async def _reset_ledger(db: AsyncSession) -> int:
    """Soft-delete (UPDATE deleted_at=NOW) all live ledger rows.

    Project rule "MAI hard delete — usare soft delete" applies here.
    The unique index ``ux_mass_balance_ledger_natural_key`` is partial
    (``WHERE deleted_at IS NULL``), so soft-deleted rows do not collide
    with the upsert during the rebuild. Audit trail is preserved: an
    operator can diff old vs new by toggling ``deleted_at``.
    """
    r = await db.execute(text(
        "UPDATE mass_balance_ledger SET deleted_at = NOW() "
        "WHERE deleted_at IS NULL"
    ))
    return r.rowcount or 0


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill mass_balance_ledger warehouse events.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect + report only; do not write rows.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="DELETE all mass_balance_ledger rows before backfilling.",
    )
    parser.add_argument(
        "--from-date",
        default=_OPENING_DEFAULT_DATE.isoformat(),
        help=(
            "Only replay source rows strictly AFTER this ISO date "
            f"(default {_OPENING_DEFAULT_DATE.isoformat()}; opening "
            "events are anchored to this date)."
        ),
    )
    args = parser.parse_args()

    try:
        from_date = date.fromisoformat(args.from_date)
    except ValueError:
        parser.error(
            f"--from-date must be YYYY-MM-DD (got {args.from_date!r})"
        )

    started_at = datetime.utcnow()
    print(
        f"[{started_at.isoformat(timespec='seconds')}Z] "
        f"backfill_warehouse starting "
        f"(from-date={from_date.isoformat()}, "
        f"dry_run={args.dry_run}, reset={args.reset}, "
        f"discharge_trigger={DISCHARGE_TRIGGER})"
    )

    # ------------------------------------------------------------------
    # 1. Reset (optional) + collect events from sources
    # ------------------------------------------------------------------
    async with async_session_factory() as db:
        if args.reset and not args.dry_run:
            deleted = await _reset_ledger(db)
            await db.commit()
            print(f"  reset: deleted {deleted} pre-existing ledger rows")
        elif args.reset and args.dry_run:
            print("  reset: SKIPPED (dry-run)")

        # Build event list
        events: list[dict] = []
        # Opening rows are always included. When the natural key already
        # exists in mass_balance_ledger the UPSERT (ON CONFLICT … DO
        # UPDATE) is a no-op on the kg_in/kg_out values, but the events
        # remaining in `events` seed `_compute_balances` with the correct
        # opening balance per product_kind — without them the running
        # balance restarts from zero and downstream prev/post_balance_kg
        # values are shifted by the opening amount.
        events.extend(_opening_events(from_date))

        events.extend(await _production_events(db, from_date))
        events.extend(await _consignment_events(db, from_date))
        events.extend(await _byproduct_sale_events(db, from_date))

    # ------------------------------------------------------------------
    # 2. Compute per-product running balances
    # ------------------------------------------------------------------
    _compute_balances(events)

    # ------------------------------------------------------------------
    # 3. Pre-write summary by event_type
    # ------------------------------------------------------------------
    type_counts: dict[str, int] = {}
    for ev in events:
        type_counts[ev["event_type"]] = type_counts.get(
            ev["event_type"], 0
        ) + 1
    print("  Event-type counts (pre-upsert):")
    for t, n in sorted(type_counts.items()):
        print(f"    {t:18s} {n}")

    if args.dry_run:
        print(f"DRY-RUN: would upsert {len(events)} rows. Aborting.")
        _print_summary(events)
        return

    # ------------------------------------------------------------------
    # 4. Upsert
    # ------------------------------------------------------------------
    async with async_session_factory() as db:
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

    finished_at = datetime.utcnow()
    print(
        f"[{finished_at.isoformat(timespec='seconds')}Z] "
        f"backfill_warehouse done: {len(events)} rows "
        f"({inserted} inserted, {updated} updated) in "
        f"{(finished_at - started_at).total_seconds():.1f}s."
    )

    _print_summary(events)


def _print_summary(events: list[dict]) -> None:
    """Final per-product table: events inserted, final balance kg."""
    per_kind_count: dict[str, int] = {}
    per_kind_final: dict[str, Decimal] = {}
    for ev in events:
        k = ev["product_kind"]
        per_kind_count[k] = per_kind_count.get(k, 0) + 1
        per_kind_final[k] = ev["post_balance_kg"]  # last write wins (sorted)

    print()
    print(f"  {'product_kind':<14s} {'events':>10s} {'final_balance_kg':>22s}")
    print(f"  {'-' * 14:<14s} {'-' * 10:>10s} {'-' * 22:>22s}")
    for kind in _OPENING_BALANCES:  # stable order
        cnt = per_kind_count.get(kind, 0)
        bal = per_kind_final.get(kind, Decimal(0))
        print(f"  {kind:<14s} {cnt:>10d} {bal:>22}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
