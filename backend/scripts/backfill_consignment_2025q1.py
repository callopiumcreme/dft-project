"""Backfill script: Q1-2025 Crown Oil consignment (DEL-CRW-2025-1).

Creates the Q1 2025 consignment + 12 ``consignment_pos`` rows so that the
``mass_balance_ledger`` can register the early-2025 EU oil discharges
(``event_type='pos_issue'``). Total mass = 304820.000 kg (exact).

Source data
-----------
Drive scout 2026-05-24 of ``DFT_2025/CROWN POS VECCHI/``. Twelve PoS PDFs
matching ``ISCC_EU_PoS_PO#NNNN.pdf`` reconciled to 100 % accuracy against
the underlying PO numbers (1177, 1178, 1179, 1180, 1181, 1182, 1183, 1184,
1185, 1186, 1240, 1242).

Refuso (typo) handling
----------------------
The three PoS PDFs for PO#1186, #1240, #1242 each print
``Date of issuance of the PoS: 29.02.2025``. 2025 is NOT a leap year, so
that date is invalid. Per operator decision (logged 2026-05-24) the
canonical remap is ``2025-03-01``. The remap is applied **at the
data-table definition site below** (NOT at insert time): the row literal
already carries ``date(2025, 3, 1)``, leaving a clear git-diff trail.

Idempotency
-----------
Re-running produces the same DB state:

* ``consignment`` upsert keyed on ``code``;
* ``consignment_pos`` upsert keyed on ``(consignment_id, pos_number)``.

Both clauses overwrite the numeric / date fields with the values defined
here, so this script is the canonical source for those columns.

Usage
-----
::

    cd backend
    DATABASE_URL=postgresql+asyncpg://dft:dft@172.22.0.2:5432/dft \\
        python scripts/backfill_consignment_2025q1.py [--dry-run] [--force]

    # or, inside the dft-project_internal network where hostname 'db' resolves:
    python scripts/backfill_consignment_2025q1.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path injection (so ``python scripts/...`` works without -m)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_VERSION = "1.0.0"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dft@172.22.0.2:5432/dft",
)

_GDRIVE_POS_BASE = "gdrive:DFT_2025/CROWN POS VECCHI"


def _pos_pdf_ref(po_number: str) -> str:
    """Return the gdrive path for the PoS PDF backing a given PO number."""
    return f"{_GDRIVE_POS_BASE}/ISCC_EU_PoS_PO#{po_number}.pdf"


# ---------------------------------------------------------------------------
# Off-taker + consignment constants
# ---------------------------------------------------------------------------

OFF_TAKER_CODE = "CROWN-OIL-UK"

CONSIGNMENT_CODE = "DEL-CRW-2025-1"
CONSIGNMENT_PRODUCT_GRADE = "DEV-P100"
CONSIGNMENT_PROD_DATE_FROM = date(2025, 1, 21)
CONSIGNMENT_PROD_DATE_TO = date(2025, 3, 1)
CONSIGNMENT_TOTAL_KG = Decimal("304820.000")
CONSIGNMENT_STATUS = "delivered_uk"
CONSIGNMENT_NOTES = (
    "Backfill Q1 2025 (12 POS, OISCRO-0001-25..0012-25). "
    "Source: Drive /CROWN POS VECCHI/ scouted 2026-05-24. "
    "Refuso 29.02.2025 -> 2025-03-01 for PO#1186/1240/1242 per operator decision."
)

# ---------------------------------------------------------------------------
# Q1 2025 PoS data (12 rows, total 304820.000 kg).
#
# Refuso remap is applied here at definition time: PO#1186/1240/1242 ship
# with PDF date '29.02.2025' (invalid -- 2025 is not a leap year). The
# operator's canonical remap is 2025-03-01, hard-coded as date(2025, 3, 1).
# ---------------------------------------------------------------------------

Q1_POS_ROWS: list[dict[str, object]] = [
    {
        "pos_number": "OISCRO-0001-25",
        "kg_net": Decimal("26221.000"),
        "issuance_date": date(2025, 1, 22),
        "dispatch_date": date(2025, 1, 21),
        "po_number": "1177",
    },
    {
        "pos_number": "OISCRO-0002-25",
        "kg_net": Decimal("26181.000"),
        "issuance_date": date(2025, 1, 22),
        "dispatch_date": date(2025, 1, 21),
        "po_number": "1178",
    },
    {
        "pos_number": "OISCRO-0003-25",
        "kg_net": Decimal("26091.000"),
        "issuance_date": date(2025, 2, 3),
        "dispatch_date": date(2025, 2, 3),
        "po_number": "1179",
    },
    {
        "pos_number": "OISCRO-0004-25",
        "kg_net": Decimal("26089.000"),
        "issuance_date": date(2025, 2, 4),
        "dispatch_date": date(2025, 2, 4),
        "po_number": "1180",
    },
    {
        "pos_number": "OISCRO-0005-25",
        "kg_net": Decimal("24900.000"),
        "issuance_date": date(2025, 2, 22),
        "dispatch_date": date(2025, 2, 21),
        "po_number": "1184",
    },
    {
        "pos_number": "OISCRO-0006-25",
        "kg_net": Decimal("24160.000"),
        "issuance_date": date(2025, 2, 22),
        "dispatch_date": date(2025, 2, 21),
        "po_number": "1185",
    },
    {
        "pos_number": "OISCRO-0007-25",
        "kg_net": Decimal("26107.000"),
        "issuance_date": date(2025, 2, 6),
        "dispatch_date": date(2025, 2, 6),
        "po_number": "1181",
    },
    {
        "pos_number": "OISCRO-0008-25",
        "kg_net": Decimal("26103.000"),
        "issuance_date": date(2025, 2, 6),
        "dispatch_date": date(2025, 2, 6),
        "po_number": "1182",
    },
    {
        "pos_number": "OISCRO-0009-25",
        "kg_net": Decimal("26068.000"),
        "issuance_date": date(2025, 2, 7),
        "dispatch_date": date(2025, 2, 7),
        "po_number": "1183",
    },
    {
        # PDF refuso: prints 29.02.2025 (invalid). Operator remap -> 2025-03-01.
        "pos_number": "OISCRO-0010-25",
        "kg_net": Decimal("23240.000"),
        "issuance_date": date(2025, 3, 1),
        "dispatch_date": date(2025, 2, 28),
        "po_number": "1186",
    },
    {
        # PDF refuso: prints 29.02.2025 (invalid). Operator remap -> 2025-03-01.
        "pos_number": "OISCRO-0011-25",
        "kg_net": Decimal("26680.000"),
        "issuance_date": date(2025, 3, 1),
        "dispatch_date": date(2025, 2, 28),
        "po_number": "1240",
    },
    {
        # PDF refuso: prints 29.02.2025 (invalid). Operator remap -> 2025-03-01.
        "pos_number": "OISCRO-0012-25",
        "kg_net": Decimal("22980.000"),
        "issuance_date": date(2025, 3, 1),
        "dispatch_date": date(2025, 2, 28),
        "po_number": "1242",
    },
]

EXPECTED_TOTAL_KG = Decimal("304820.000")


def _validate_table() -> None:
    """Sanity-check the in-module data table before any DB I/O."""
    if len(Q1_POS_ROWS) != 12:
        raise RuntimeError(f"Expected 12 Q1 POS rows, got {len(Q1_POS_ROWS)}")

    total = sum((Decimal(str(r["kg_net"])) for r in Q1_POS_ROWS), Decimal("0"))
    if total != EXPECTED_TOTAL_KG:
        raise RuntimeError(
            f"Q1 POS total mismatch: expected {EXPECTED_TOTAL_KG}, got {total}"
        )

    pos_numbers = [str(r["pos_number"]) for r in Q1_POS_ROWS]
    if len(set(pos_numbers)) != len(pos_numbers):
        raise RuntimeError("Duplicate pos_number entries in Q1_POS_ROWS")


# ---------------------------------------------------------------------------
# Main backfill
# ---------------------------------------------------------------------------


async def run_backfill(
    session: AsyncSession,
    *,
    dry_run: bool,
    force: bool,
) -> None:
    # ------------------------------------------------------------------ #
    # 1. off_taker lookup                                                  #
    # ------------------------------------------------------------------ #
    row = await session.execute(
        text(
            "SELECT id FROM off_taker "
            "WHERE code = :code AND deleted_at IS NULL"
        ),
        {"code": OFF_TAKER_CODE},
    )
    off_taker_id: int | None = row.scalar_one_or_none()
    if off_taker_id is None:
        raise RuntimeError(
            f"off_taker {OFF_TAKER_CODE!r} not found (or soft-deleted). "
            "Run the Q3 backfill first (it seeds this row) or insert it manually."
        )

    # ------------------------------------------------------------------ #
    # 2. consignment -- check existence and warn if force is not set       #
    # ------------------------------------------------------------------ #
    existing = await session.execute(
        text(
            "SELECT id FROM consignment "
            "WHERE code = :code AND deleted_at IS NULL"
        ),
        {"code": CONSIGNMENT_CODE},
    )
    existing_id = existing.scalar_one_or_none()
    if existing_id is not None and not force:
        print(
            f"NOTE: consignment {CONSIGNMENT_CODE!r} already exists "
            f"(id={existing_id}); proceeding with upsert. "
            "Pass --force only if you want this banner silenced."
        )

    cons_sql = text(
        """
        INSERT INTO consignment
            (code, off_taker_id, product_grade,
             prod_date_from, prod_date_to, total_kg, status, notes,
             created_at, updated_at)
        VALUES
            (:code, :off_taker_id, :product_grade,
             :prod_date_from, :prod_date_to, :total_kg, :status, :notes,
             NOW(), NOW())
        ON CONFLICT (code) DO UPDATE
            SET off_taker_id    = EXCLUDED.off_taker_id,
                product_grade   = EXCLUDED.product_grade,
                prod_date_from  = EXCLUDED.prod_date_from,
                prod_date_to    = EXCLUDED.prod_date_to,
                total_kg        = EXCLUDED.total_kg,
                status          = EXCLUDED.status,
                notes           = EXCLUDED.notes,
                updated_at      = NOW()
        """
    )
    cons_params = {
        "code": CONSIGNMENT_CODE,
        "off_taker_id": off_taker_id,
        "product_grade": CONSIGNMENT_PRODUCT_GRADE,
        "prod_date_from": CONSIGNMENT_PROD_DATE_FROM,
        "prod_date_to": CONSIGNMENT_PROD_DATE_TO,
        "total_kg": CONSIGNMENT_TOTAL_KG,
        "status": CONSIGNMENT_STATUS,
        "notes": CONSIGNMENT_NOTES,
    }

    if dry_run:
        print("[dry-run] would upsert consignment:")
        print(f"  SQL: {cons_sql.text.strip().splitlines()[0]} ...")
        print(f"  params: code={CONSIGNMENT_CODE!r} total_kg={CONSIGNMENT_TOTAL_KG} "
              f"status={CONSIGNMENT_STATUS} off_taker_id={off_taker_id}")
    else:
        await session.execute(cons_sql, cons_params)

    # Re-fetch the id (post-upsert it must exist; in dry-run use existing or 0)
    if dry_run and existing_id is None:
        consignment_id = 0
    else:
        cons_row = await session.execute(
            text("SELECT id FROM consignment WHERE code = :code"),
            {"code": CONSIGNMENT_CODE},
        )
        consignment_id = int(cons_row.scalar_one())

    # ------------------------------------------------------------------ #
    # 3. consignment_pos -- 12 upserts on (consignment_id, pos_number)    #
    # ------------------------------------------------------------------ #
    pos_sql = text(
        """
        INSERT INTO consignment_pos
            (consignment_id, pos_number, pdf_ref, kg_net, issuance_date,
             created_at)
        VALUES
            (:consignment_id, :pos_number, :pdf_ref, :kg_net, :issuance_date,
             NOW())
        ON CONFLICT (consignment_id, pos_number) DO UPDATE
            SET pdf_ref       = EXCLUDED.pdf_ref,
                kg_net        = EXCLUDED.kg_net,
                issuance_date = EXCLUDED.issuance_date
        """
    )

    for pos_row in Q1_POS_ROWS:
        po_number = str(pos_row["po_number"])
        params = {
            "consignment_id": consignment_id,
            "pos_number": str(pos_row["pos_number"]),
            "pdf_ref": _pos_pdf_ref(po_number),
            "kg_net": pos_row["kg_net"],
            "issuance_date": pos_row["issuance_date"],
        }
        if dry_run:
            print(
                f"[dry-run] would upsert consignment_pos: "
                f"pos={params['pos_number']} kg_net={params['kg_net']} "
                f"issuance_date={params['issuance_date']} "
                f"pdf_ref={params['pdf_ref']}"
            )
        else:
            await session.execute(pos_sql, params)

    # ------------------------------------------------------------------ #
    # 4. audit_log -- one row tagging the whole backfill                  #
    #                                                                     #
    # ``action`` is CHECK-constrained to                                  #
    #   {insert,update,delete,soft_delete,restore}                        #
    # so we use 'insert' and pack the semantic event_type +               #
    # script metadata into ``new_values`` JSON.                            #
    # ------------------------------------------------------------------ #
    audit_payload: dict[str, object] = {
        "event_type": "backfill_q1_consignment",
        "script": "backfill_consignment_2025q1.py",
        "script_version": SCRIPT_VERSION,
        "consignment_code": CONSIGNMENT_CODE,
        "pos_numbers": [str(r["pos_number"]) for r in Q1_POS_ROWS],
        "kg_total": str(EXPECTED_TOTAL_KG),
        "refuso_remap": {
            "from": "29.02.2025",
            "to": "2025-03-01",
            "affected_po": ["1186", "1240", "1242"],
        },
    }

    audit_sql = text(
        """
        INSERT INTO audit_log
            (table_name, record_id, action, old_values, new_values,
             changed_by, changed_at)
        VALUES
            ('consignment', :record_id, 'insert',
             NULL, CAST(:new_values AS jsonb), NULL, NOW())
        """
    )
    audit_params = {
        "record_id": consignment_id,
        "new_values": json.dumps(audit_payload),
    }

    if dry_run:
        print(
            "[dry-run] would insert audit_log row "
            f"(table=consignment record_id={consignment_id} "
            "event_type=backfill_q1_consignment)"
        )
    else:
        await session.execute(audit_sql, audit_params)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


async def verify(session: AsyncSession) -> bool:
    cons_row = await session.execute(
        text(
            "SELECT id, code, total_kg, status "
            "FROM consignment "
            "WHERE code = :code AND deleted_at IS NULL"
        ),
        {"code": CONSIGNMENT_CODE},
    )
    cons = cons_row.mappings().one_or_none()
    if cons is None:
        print(f"ERROR: consignment {CONSIGNMENT_CODE!r} not found post-backfill",
              file=sys.stderr)
        return False

    cons_id = int(cons["id"])
    cons_total = Decimal(str(cons["total_kg"]))
    cons_status = str(cons["status"])

    pos_rows = await session.execute(
        text(
            "SELECT pos_number, kg_net, issuance_date "
            "FROM consignment_pos "
            "WHERE consignment_id = :cid AND deleted_at IS NULL "
            "ORDER BY pos_number"
        ),
        {"cid": cons_id},
    )
    pos_records = pos_rows.mappings().all()
    pos_count = len(pos_records)
    pos_sum = sum(
        (Decimal(str(r["kg_net"])) for r in pos_records),
        Decimal("0"),
    )

    iss_counter: Counter[str] = Counter(
        str(r["issuance_date"]) for r in pos_records
    )

    mass_match = pos_sum == EXPECTED_TOTAL_KG
    cons_match = cons_total == EXPECTED_TOTAL_KG
    count_match = pos_count == 12
    status_match = cons_status == CONSIGNMENT_STATUS

    print()
    print("== Backfill verification (Q1 2025) ==")
    print(
        f"consignment: id={cons_id} code={cons['code']} "
        f"total_kg={cons_total} status={cons_status}"
    )
    print(f"consignment_pos count: {pos_count}")
    mass_tag = "match: OK" if mass_match else "match: MISMATCH"
    print(f"pos sum kg: {pos_sum} (expected {EXPECTED_TOTAL_KG}) [{mass_tag}]")
    print("issuance_date distribution:")
    for iss, count in sorted(iss_counter.items()):
        print(f"  {iss}: {count}")

    ok = mass_match and cons_match and count_match and status_match
    if not ok:
        print(
            "ERROR: verification failed -- "
            f"mass_match={mass_match} cons_match={cons_match} "
            f"count_match={count_match} status_match={status_match}",
            file=sys.stderr,
        )
    return ok


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL + rows that would be inserted; do not commit.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-execute even if the consignment already exists. "
            "Upsert is always idempotent, so this flag is mostly cosmetic."
        ),
    )
    args = parser.parse_args()

    _validate_table()

    engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    if args.dry_run:
        async with factory() as session:
            await run_backfill(session, dry_run=True, force=args.force)
        await engine.dispose()
        print("\n[dry-run] no changes committed.")
        return

    async with factory() as session, session.begin():
        await run_backfill(session, dry_run=False, force=args.force)

    async with factory() as session:
        ok = await verify(session)

    await engine.dispose()

    if not ok:
        sys.exit(1)

    print("\nBackfill completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
