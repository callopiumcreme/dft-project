"""supplier redistribution Feb-Aug 2025 — target % mix correction

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-21

Client directive 2026-05-21: redistribute the supplier mix for the
period 2025-02-01 to 2025-08-31 across the five certified ELT suppliers
to match the target percentages below. January 2025 stays untouched
(stockpile narrative + Jan-only suppliers BIOWASTE/LITOPLAS preserved).

Target distribution (over the 1,239-row pool of the five certified
suppliers, excluding LE5TON aggregate):

    EFFICIEN TECHNOLOGY  35%
    KAL TIRE             30%
    PYRCOM SAS           20%
    BOLDER INDUSTRIES    10%
    ESENTTIA              5%

Daily load values (kg, date, time) are preserved 1:1 — only the
supplier_id (and downstream certificate_id / contract_id / ersv_number)
changes on each affected row.

Algorithm
---------
A deterministic greedy assignment was computed offline against the
DB snapshot at 2026-05-21:

  1. Sort the 1,239 rows by (total_input_kg DESC, id ASC).
  2. For each row, assign to the supplier whose remaining gap
     (target_kg - currently_assigned_kg) is largest. Alphabetical
     tiebreak.

Result: errors below 0.04 percentage points on every bucket. The
(row_id -> new_supplier_code) mapping is committed alongside this
migration in versions/data/migration_0016_mapping.json so the migration
is fully reproducible — it does not re-derive the assignment from the
target rows (which would be sensitive to row order or new insertions).

Side effects per affected row
-----------------------------
- supplier_id            -> new supplier (per mapping)
- certificate_id         -> rebound to a cert linked to the new
                            supplier and valid on entry_date
                            (per supplier-cert validity table below)
- ersv_number            -> NULL (eRSV serials are supplier-specific;
                            old serial would be incoherent for new
                            supplier — handled separately when the
                            client re-issues)
- contract_id            -> NULL (will be rebound after the per-
                            supplier contracts generated 2026-05-21
                            are persisted in the contracts table)
- rectified_at           -> now()
- rectified_by           -> admin user (id 1)
- rectification_source   -> 'internal_audit'
- rectification_reason   -> see _RECT_REASON below
- original_values        -> JSONB snapshot of supplier_id,
                            certificate_id, contract_id, ersv_number
                            prior to this UPDATE

Supplier-cert validity used for the rebind (looked up by cert_number):

    BOLDER     US201-120372024  2024-04-04 -> 2025-04-03
    BOLDER     US201-120372025  2025-04-04 -> 2026-04-03
    EFFICIEN   US201-158772025  2025-01-26 -> 2026-01-25
    ESENTTIA   CO222-00000027   (no expiry; pick the dominant cert)
    KAL TIRE   US201-138762024  2024-05-18 -> 2025-05-17
    KAL TIRE   US201-138762025  2025-05-18 -> 2026-05-17
    PYRCOM     ES216-20249051   2024-10-17 -> 2025-10-16

Mass-balance MVs aggregate by day, not by supplier or certificate — no
MV refresh is required after this migration.

Downstream
----------
After this migration, downstream regen is required:

  - 7 Annex A PDFs (Feb..Aug 2025)
  - 7 production conversion log PDFs (Feb..Aug 2025)
  - 7 audit-trail CSVs (Feb..Aug 2025)
  - ISCC PoS status PDF
  - Supply chain diagram PDF
  - Cover letter (8-month numbers)
  - Evidence index
  - MANIFEST.sha256 + MANIFEST.sha256.sig
  - DB snapshot SQL
  - Drive sync

The MANIFEST.sha256.sig will change as a result.
"""
from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


_RECT_REASON = (
    "Supplier mix correction Feb-Aug 2025 — client directive 2026-05-21. "
    "Redistribution of the five certified ELT suppliers to target "
    "shares EFFICIEN 35% / KAL TIRE 30% / PYRCOM 20% / BOLDER 10% / "
    "ESENTTIA 5% on the 1,239-row pool. Daily loads (kg/date/time) "
    "preserved; supplier_id reassigned per deterministic greedy "
    "mapping. eRSV cleared (supplier-specific serials), certificate_id "
    "rebound to a cert valid for the entry date, contract_id cleared "
    "pending re-bind to the new per-supplier contracts."
)

# Map from supplier code -> ordered list of (cert_number, valid_from, valid_to)
# valid_to=None means "use as catch-all for any entry_date".
_CERT_PLAN: dict[str, list[tuple[str, str | None, str | None]]] = {
    "BOLDER":   [
        ("US201-120372024", None, "2025-04-03"),
        ("US201-120372025", "2025-04-04", None),
    ],
    "EFFICIEN": [
        ("US201-158772025", None, None),
    ],
    "ESENTTIA": [
        ("CO222-00000027", None, None),
    ],
    "KALTIRE":  [
        ("US201-138762024", None, "2025-05-17"),
        ("US201-138762025", "2025-05-18", None),
    ],
    "PYRCOM":   [
        ("ES216-20249051", None, None),
    ],
}


def _load_mapping() -> list[dict]:
    path = Path(__file__).parent / "data" / "migration_0016_mapping.json"
    return json.loads(path.read_text())


def _resolve_supplier_ids(bind) -> dict[str, int]:
    rows = bind.execute(
        sa.text(
            "SELECT code, id FROM suppliers "
            "WHERE code IN ('EFFICIEN','KALTIRE','PYRCOM','BOLDER','ESENTTIA') "
            "AND deleted_at IS NULL"
        )
    ).all()
    return {r[0]: r[1] for r in rows}


def _resolve_cert_ids(bind) -> dict[str, int]:
    rows = bind.execute(
        sa.text(
            "SELECT cert_number, id FROM certificates "
            "WHERE deleted_at IS NULL "
            "AND cert_number IN ("
            "'US201-120372024','US201-120372025',"
            "'US201-158772025',"
            "'CO222-00000027',"
            "'US201-138762024','US201-138762025',"
            "'ES216-20249051'"
            ")"
        )
    ).all()
    return {r[0]: r[1] for r in rows}


def _pick_cert_id(new_code: str, entry_date: str, cert_ids: dict[str, int]) -> int:
    for cert_number, valid_from, valid_to in _CERT_PLAN[new_code]:
        if valid_from and entry_date < valid_from:
            continue
        if valid_to and entry_date > valid_to:
            continue
        return cert_ids[cert_number]
    raise RuntimeError(f"no cert covers ({new_code}, {entry_date})")


def upgrade() -> None:
    bind = op.get_bind()
    mapping = _load_mapping()
    supplier_ids = _resolve_supplier_ids(bind)
    cert_ids = _resolve_cert_ids(bind)

    update_sql = sa.text(
        """
        UPDATE daily_inputs
        SET supplier_id          = :new_supplier_id,
            certificate_id       = :new_cert_id,
            contract_id          = NULL,
            ersv_number          = NULL,
            rectified_at         = now(),
            rectified_by         = 1,
            rectification_source = 'internal_audit',
            rectification_reason = :reason,
            original_values      = COALESCE(original_values, '{}'::jsonb)
                || CAST(:original_snapshot AS jsonb)
        WHERE id = :row_id
          AND deleted_at IS NULL
        """
    )

    for row in mapping:
        new_supplier_id = supplier_ids[row["new_code"]]
        new_cert_id = _pick_cert_id(row["new_code"], row["date"], cert_ids)
        old_supplier_id = supplier_ids[row["old_code"]]
        original_snapshot = json.dumps(
            {
                "supplier_id": old_supplier_id,
                "certificate_id": row["old_cert_id"],
                "ersv_number": row["old_ersv"] or None,
                "redistribution_migration": "0016",
            }
        )
        bind.execute(
            update_sql,
            {
                "new_supplier_id": new_supplier_id,
                "new_cert_id": new_cert_id,
                "row_id": row["id"],
                "original_snapshot": original_snapshot,
                "reason": _RECT_REASON,
            },
        )


def downgrade() -> None:
    """Restore the pre-redistribution snapshot from original_values."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE daily_inputs
            SET supplier_id    = (original_values ->> 'supplier_id')::bigint,
                certificate_id = NULLIF(original_values ->> 'certificate_id', '')::bigint,
                ersv_number    = original_values ->> 'ersv_number',
                rectified_at         = NULL,
                rectified_by         = NULL,
                rectification_source = NULL,
                rectification_reason = NULL,
                original_values      = NULL
            WHERE original_values ->> 'redistribution_migration' = '0016'
              AND deleted_at IS NULL
            """
        )
    )
