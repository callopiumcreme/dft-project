"""eRSV serial regeneration Feb-Aug 2025 (non-LE5TON suppliers)

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-22

Sequel to migration 0016 (supplier redistribution Feb-Aug 2025), which
cleared ``ersv_number`` on every Feb..Aug 2025 row whose supplier was
reassigned (eRSV serials are supplier-specific, so old serials would be
incoherent for the new supplier).

This migration repopulates ``ersv_number`` for those rows using an
independent per-supplier annual counter, format ``NNNNN/YY``:

    - 5-digit zero-padded counter, reset PER supplier
    - 2-digit year (entry_date.year % 100)
    - Deterministic order: ``entry_date ASC, id ASC``
    - Suppliers iterated in fixed tuple order

Scope
-----
- ``entry_date >= '2025-02-01' AND entry_date < '2025-09-01'``
- ``deleted_at IS NULL``
- Suppliers: BOLDER, EFFICIEN, ESENTTIA, KALTIRE, PYRCOM (the five
  certified ELT suppliers redistributed by 0016)

Out of scope
------------
- January 2025: FROZEN, separate numbering space ``NNN/25`` (already
  submitted in the RTFO-310125 bundle). Untouched.
- LE5TON aggregate (Feb..Aug): handled by a separate doc TBD with
  the client; excluded from this migration.

Idempotency
-----------
Each affected row stores ``ersv_regen_migration = '0017'`` inside
``original_values``. Rows already carrying that marker are skipped, so
re-running upgrade is a no-op.

Audit columns
-------------
Same pattern as 0016: ``rectified_at = now()``, ``rectified_by = 1``,
``rectification_source = 'internal_audit'``, ``rectification_reason =
_RECT_REASON``. ``original_values`` is extended (not replaced) with the
pre-0017 ``ersv_number`` snapshot and the migration marker.

Downgrade
---------
Restores ``ersv_number`` from the snapshot and strips the two 0017 keys
from ``original_values``. Does NOT null the ``rectified_*`` columns —
0016 set those on the same rows for a different reason; preserving them
keeps the 0016 audit trail intact.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa

from alembic import op

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


SUPPLIER_CODES = ("BOLDER", "EFFICIEN", "ESENTTIA", "KALTIRE", "PYRCOM")

_RECT_REASON = (
    "eRSV serial regeneration Feb-Aug 2025 (non-LE5TON suppliers). "
    "Per-supplier independent annual counter, format NNNNN/YY, "
    "ordered by entry_date ASC, id ASC. Jan 2025 untouched (separate "
    "frozen numbering space NNN/25). LE5TON excluded (separate doc TBD). "
    "Migration 0017."
)


def _resolve_supplier_ids(bind: Connection) -> dict[str, int]:
    rows = bind.execute(
        sa.text(
            "SELECT code, id FROM suppliers "
            "WHERE code IN :codes AND deleted_at IS NULL"
        ).bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": list(SUPPLIER_CODES)},
    ).all()
    return {r[0]: r[1] for r in rows}


def upgrade() -> None:
    bind = op.get_bind()
    supplier_ids = _resolve_supplier_ids(bind)
    missing = [c for c in SUPPLIER_CODES if c not in supplier_ids]
    assert not missing, f"Suppliers not resolved (code -> id): {missing}"  # noqa: S101 — Architect plan requires loud failure on missing supplier

    select_sql = sa.text(
        """
        SELECT id, entry_date, ersv_number
        FROM daily_inputs
        WHERE supplier_id = :sid
          AND entry_date >= DATE '2025-02-01'
          AND entry_date <  DATE '2025-09-01'
          AND deleted_at IS NULL
          AND (
                original_values IS NULL
             OR NOT (original_values ? 'ersv_regen_migration')
          )
        ORDER BY entry_date ASC, id ASC
        """
    )

    update_sql = sa.text(
        """
        UPDATE daily_inputs
        SET ersv_number          = :new_ersv,
            rectified_at         = now(),
            rectified_by         = 1,
            rectification_source = 'internal_audit',
            rectification_reason = :reason,
            original_values      = COALESCE(original_values, '{}'::jsonb)
                || jsonb_build_object(
                       'ersv_number_pre_0017', ersv_number,
                       'ersv_regen_migration', '0017'
                   )
        WHERE id = :row_id
          AND deleted_at IS NULL
        """
    )

    for code in SUPPLIER_CODES:
        sid = supplier_ids[code]
        rows = bind.execute(select_sql, {"sid": sid}).all()
        for counter, (row_id, entry_date, _old_ersv) in enumerate(rows, start=1):
            yy = entry_date.year % 100
            new_ersv = f"{counter:05d}/{yy:02d}"
            bind.execute(
                update_sql,
                {
                    "new_ersv": new_ersv,
                    "reason": _RECT_REASON,
                    "row_id": row_id,
                },
            )


def downgrade() -> None:
    """Restore pre-0017 ersv_number; preserve 0016 rectified_* columns."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE daily_inputs
            SET ersv_number     = original_values ->> 'ersv_number_pre_0017',
                original_values = NULLIF(
                                      original_values
                                        - 'ersv_number_pre_0017'
                                        - 'ersv_regen_migration',
                                      '{}'::jsonb)
            WHERE deleted_at IS NULL
              AND original_values ? 'ersv_regen_migration'
              AND original_values ->> 'ersv_regen_migration' = '0017'
            """
        )
    )
