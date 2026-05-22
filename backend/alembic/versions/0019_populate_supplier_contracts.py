"""Populate supplier contracts metadata Feb–Aug 2025

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-22

Backfill ``contracts`` rows with metadata extracted from signed
contract documents in ``DFT_2025/Contracts`` Drive folder.

UPDATEs (3 existing rows already in DB, missing dates+kg):
    BW200224 BIOWASTE  → 2025-01-01..2025-06-30, 9,000,000 kg
    ES400125 ESENTTIA  → 2025-01-01..2025-06-30, 12,000,000 kg
    LP300324 LITOPLAS  → 2025-01-01..2025-06-30, 3,000,000 kg

INSERTs (4 new redistribution suppliers Feb-Aug 2025, no DB row yet):
    BO150225 BOLDER    → 2025-02-01..2025-08-31, 1,925,000 kg
    EF010225 EFFICIEN  → 2025-02-01..2025-08-31, 6,825,000 kg
    KT200125 KALTIRE   → 2025-02-01..2025-08-31, 5,775,000 kg
    PY250125 PYRCOM    → 2025-02-01..2025-08-31, 3,850,000 kg

Cleanup soft-deletes:
    id=5 ``-`` orphan placeholder (no supplier_id, ingest artefact)
    id=6 ``E2E-CTR-404437`` test contract leaked into prod

total_kg_committed = monthly_mt × months × 1000 kg/mt
    BW: 1500 × 6
    ES: 2000 × 6
    LP:  500 × 6
    BO:  275 × 7
    EF:  975 × 7
    KT:  825 × 7
    PY:  550 × 7

Suppliers id resolved via ``code`` (NOT hard-coded) for portability
across envs (lesson from 0016).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from alembic import op
from sqlalchemy import text

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


JAN_JUN_START = date(2025, 1, 1)
JAN_JUN_END = date(2025, 6, 30)
FEB_AUG_START = date(2025, 2, 1)
FEB_AUG_END = date(2025, 8, 31)


EXISTING_UPDATES = [
    # (contract_code, supplier_code, start, end, total_kg, note)
    ("BW200224", "BIOWASTE", JAN_JUN_START, JAN_JUN_END, Decimal("9000000.000"),
     "1500 mt mensuales (±10%), Enero–Junio 2025, ELT HS 40122000"),
    ("ES400125", "ESENTTIA", JAN_JUN_START, JAN_JUN_END, Decimal("12000000.000"),
     "2000 mt mensuales (±20%), Enero–Junio 2025, ELT HS 40122000"),
    ("LP300324", "LITOPLAS", JAN_JUN_START, JAN_JUN_END, Decimal("3000000.000"),
     "500 mt mensuales (±20%), Enero–Junio 2025, ELT HS 40122000"),
]


NEW_INSERTS = [
    # (contract_code, supplier_code, start, end, total_kg, note)
    ("BO150225", "BOLDER", FEB_AUG_START, FEB_AUG_END, Decimal("1925000.000"),
     "275 mt monthly (±20%), February–August 2025, ELT HS 40122000"),
    ("EF010225", "EFFICIEN", FEB_AUG_START, FEB_AUG_END, Decimal("6825000.000"),
     "975 mt monthly (±20%), February–August 2025, ELT HS 40122000"),
    ("KT200125", "KALTIRE", FEB_AUG_START, FEB_AUG_END, Decimal("5775000.000"),
     "825 mt monthly (±20%), February–August 2025, ELT HS 40122000"),
    ("PY250125", "PYRCOM", FEB_AUG_START, FEB_AUG_END, Decimal("3850000.000"),
     "550 mt mensuales (±20%), Febrero–Agosto 2025, ELT HS 40122000"),
]


CLEANUP_CODES = ["-", "E2E-CTR-404437"]


def upgrade() -> None:
    conn = op.get_bind()

    for code, sup_code, start, end, total_kg, note in EXISTING_UPDATES:
        sup_id = conn.execute(
            text("SELECT id FROM suppliers WHERE code = :c"), {"c": sup_code}
        ).scalar()
        if sup_id is None:
            raise RuntimeError(f"supplier {sup_code} missing — abort")
        result = conn.execute(
            text(
                """
                UPDATE contracts
                SET start_date = :start,
                    end_date = :end,
                    total_kg_committed = :kg,
                    supplier_id = :sup_id,
                    notes = COALESCE(notes, '') ||
                            CASE WHEN COALESCE(notes,'') = '' THEN :note
                                 ELSE E'\n' || :note END,
                    updated_at = NOW()
                WHERE code = :code
                  AND deleted_at IS NULL
                """
            ),
            {"start": start, "end": end, "kg": total_kg,
             "sup_id": sup_id, "note": note, "code": code},
        )
        if result.rowcount != 1:
            raise RuntimeError(f"UPDATE {code} affected {result.rowcount} rows, expected 1")

    for code, sup_code, start, end, total_kg, note in NEW_INSERTS:
        sup_id = conn.execute(
            text("SELECT id FROM suppliers WHERE code = :c"), {"c": sup_code}
        ).scalar()
        if sup_id is None:
            raise RuntimeError(f"supplier {sup_code} missing — abort")
        exists = conn.execute(
            text("SELECT id FROM contracts WHERE code = :code"), {"code": code}
        ).scalar()
        if exists is not None:
            raise RuntimeError(f"contract {code} already exists (id={exists}) — abort")
        conn.execute(
            text(
                """
                INSERT INTO contracts
                    (code, supplier_id, start_date, end_date,
                     total_kg_committed, is_placeholder, notes,
                     created_at, updated_at)
                VALUES
                    (:code, :sup_id, :start, :end,
                     :kg, FALSE, :note,
                     NOW(), NOW())
                """
            ),
            {"code": code, "sup_id": sup_id, "start": start, "end": end,
             "kg": total_kg, "note": note},
        )

    for code in CLEANUP_CODES:
        conn.execute(
            text(
                """
                UPDATE contracts
                SET deleted_at = NOW(), updated_at = NOW()
                WHERE code = :code AND deleted_at IS NULL
                """
            ),
            {"code": code},
        )


def downgrade() -> None:
    conn = op.get_bind()

    for code in CLEANUP_CODES:
        conn.execute(
            text("UPDATE contracts SET deleted_at = NULL WHERE code = :code"),
            {"code": code},
        )

    for code, *_ in NEW_INSERTS:
        conn.execute(text("DELETE FROM contracts WHERE code = :code"), {"code": code})

    for code, *_ in EXISTING_UPDATES:
        conn.execute(
            text(
                """
                UPDATE contracts
                SET start_date = NULL,
                    end_date = NULL,
                    total_kg_committed = NULL,
                    updated_at = NOW()
                WHERE code = :code
                """
            ),
            {"code": code},
        )
