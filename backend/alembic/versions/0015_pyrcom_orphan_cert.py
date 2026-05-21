"""assign PYRCOM SAS ISCC PLUS cert to the one orphan daily_inputs row

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-21

Follow-up to migration 0010 (Feb-2025 ISCC PoS cert correction). The
0010 UPDATE was guarded by ``certificate_id <> :new_cert_id`` which
evaluates to NULL — and therefore filters OUT — rows where
``certificate_id`` is already NULL. Exactly one PYRCOM SAS row was
caught by that gap:

    entry_date     supplier    total_input_kg    certificate_id
    2025-04-22     PYRCOM SAS  10 455            NULL

Pre-existing ``original_values`` on the row record the prior supplier
rename (BIOWASTE -> PYRCOM SAS, migration 0008) but no
``certificate_id`` was ever stored, because the supplier-rename
migration left it NULL pending the ISCC PoS numbers that arrived later
(migration 0010).

This migration re-points that single row to the existing PYRCOM SAS
cert ``ES216-20249051`` (id depends on environment — looked up by
``cert_number``) inserted by 0010. Validity window 2024-10-17 ->
2025-10-16 fully contains 2025-04-22.

Audit trail follows the migration 0006 + 0010 pattern: ``rectified_at``
+ ``rectification_source`` + ``rectification_reason`` stamped, prior
``certificate_id`` (NULL) preserved in ``original_values`` so the
operation is reversible. The PYRCOM feedstock-mismatch warning from
0010 is repeated verbatim in the reason because the same audit caveat
applies.

Mass-balance MVs aggregate by day, not by certificate — no MV refresh
required.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


_CERT_NUMBER = "ES216-20249051"

_RECT_REASON = (
    "Follow-up to migration 0010 (client directive 2026-05-21): "
    "supplier PYRCOM SAS row 2025-04-22 / 10 455 kg had "
    "certificate_id = NULL, so the 0010 UPDATE (guarded by "
    "certificate_id <> new_cert_id, which is NULL-unsafe) skipped "
    "it. Re-pointed to ES216-20249051 (valid 2024-10-17 -> "
    "2025-10-16). "
    "WARNING: PYRCOM cert annex declares 'Mixed plastic waste' "
    "feedstock; project operational feedstock = ELT. Pending cert "
    "annex correction."
)


def upgrade() -> None:
    bind = op.get_bind()

    cert_id = bind.execute(
        sa.text(
            "SELECT id FROM certificates "
            "WHERE cert_number = :n AND deleted_at IS NULL"
        ),
        {"n": _CERT_NUMBER},
    ).scalar_one()

    bind.execute(
        sa.text(
            """
            UPDATE daily_inputs
            SET certificate_id       = :new_cert_id,
                rectified_at         = now(),
                rectification_source = 'other',
                rectification_reason = :reason,
                original_values      = COALESCE(original_values, '{}'::jsonb)
                    || jsonb_build_object('certificate_id', NULL::bigint)
            WHERE supplier_id = (
                    SELECT id FROM suppliers
                    WHERE name = 'PYRCOM SAS' AND deleted_at IS NULL)
              AND entry_date = DATE '2025-04-22'
              AND certificate_id IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"new_cert_id": cert_id, "reason": _RECT_REASON},
    )


def downgrade() -> None:
    bind = op.get_bind()

    cert_id = bind.execute(
        sa.text(
            "SELECT id FROM certificates "
            "WHERE cert_number = :n AND deleted_at IS NULL"
        ),
        {"n": _CERT_NUMBER},
    ).scalar_one_or_none()
    if cert_id is None:
        return

    bind.execute(
        sa.text(
            """
            UPDATE daily_inputs
            SET certificate_id       = NULL,
                rectified_at         = NULL,
                rectification_source = NULL,
                rectification_reason = NULL,
                original_values      = NULLIF(
                    original_values - 'certificate_id',
                    '{}'::jsonb)
            WHERE supplier_id = (
                    SELECT id FROM suppliers
                    WHERE name = 'PYRCOM SAS' AND deleted_at IS NULL)
              AND entry_date = DATE '2025-04-22'
              AND certificate_id = :cert_id
              AND original_values ? 'certificate_id'
              AND (original_values->>'certificate_id') IS NULL
            """
        ),
        {"cert_id": cert_id},
    )
