"""supplier rename effective Feb 2025 — 4 new ELT tyre suppliers

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-19

Client directive (2026-05-19): the ELT tyre feedstock suppliers recorded
for February 2025 onward are DIFFERENT legal entities from the January
2025 suppliers — not renames of the same company. January 2025 is frozen
(already submitted in the RTFO-310125 bundle) and is left untouched.

Rename map (effective entry_date >= 2025-02-01):

    BIOWASTE   ->  PYRCOM SAS
    LITOPLAS   ->  KAL TIRE
    CIECOGRAS  ->  EFFICIEN TECHNOLOGY
    SANIMAX    ->  BOLDER INDUSTRIES

ESENTTIA and the "<=5 TON" aggregate are unchanged. ECODIESEL is untouched.

Because suppliers.name carries a UNIQUE constraint and BIOWASTE / LITOPLAS
still own legitimate January rows, this is NOT an in-place rename. Four
NEW supplier rows are inserted and daily_inputs from 2025-02-01 onward are
re-pointed to them. The original BIOWASTE / LITOPLAS / CIECOGRAS / SANIMAX
rows stay active=true and keep their January data + ISCC certificate links.

Each re-pointed daily_inputs row is soft-rectified using the audit columns
from migration 0006: original_values snapshots the pre-rename supplier_id +
name; rectified_at / rectification_source / rectification_reason record the
change for ISCC EU audit traceability. No hard delete, no rewrite of
historical attribution — the original is preserved in original_values.

NOT handled here — separate follow-up when the numbers arrive: the ISCC
certificate correction. The new suppliers do NOT inherit the old
certificates. Feb->Aug daily_inputs still carry their old certificate_id,
so supplier-breakdown reports will show stale ISCC cert numbers for the
new suppliers until a cert-correction migration re-points certificate_id
and supplier_certificates with the new ISCC PoS numbers.

Mass-balance MVs aggregate kg/litres by day, not by supplier — supplier
re-pointing changes no totals, so no MV refresh is required.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_RENAME_CUTOVER = "2025-02-01"

# old_name -> (new_name, new_code)
_RENAMES = (
    ("BIOWASTE", "PYRCOM SAS", "PYRCOM"),
    ("LITOPLAS", "KAL TIRE", "KALTIRE"),
    ("CIECOGRAS", "EFFICIEN TECHNOLOGY", "EFFICIEN"),
    ("SANIMAX", "BOLDER INDUSTRIES", "BOLDER"),
)

_RECT_REASON = (
    "Supplier rename effective Feb 2025 (client directive 2026-05-19): "
    "{old} -> {new}. Different legal entity; January 2025 left intact."
)


def upgrade() -> None:
    bind = op.get_bind()
    for old_name, new_name, new_code in _RENAMES:
        old = bind.execute(
            sa.text("SELECT id FROM suppliers WHERE name = :n AND deleted_at IS NULL"),
            {"n": old_name},
        ).first()
        if old is None:
            raise RuntimeError(f"Supplier {old_name!r} not found — migration aborted")
        old_id = old[0]

        new_id = bind.execute(
            sa.text(
                """
                INSERT INTO suppliers (name, code, country, active, is_aggregate)
                VALUES (:name, :code, NULL, true, false)
                RETURNING id
                """
            ),
            {"name": new_name, "code": new_code},
        ).scalar_one()

        bind.execute(
            sa.text(
                """
                UPDATE daily_inputs
                SET supplier_id          = :new_id,
                    rectified_at         = now(),
                    rectification_source = 'other',
                    rectification_reason = :reason,
                    original_values      = COALESCE(original_values, '{}'::jsonb)
                        || jsonb_build_object(
                               'supplier_id', supplier_id,
                               'supplier_name', CAST(:old_name AS text))
                WHERE supplier_id = :old_id
                  AND entry_date >= DATE '"""
                + _RENAME_CUTOVER
                + """'
                  AND deleted_at IS NULL
                """
            ),
            {
                "new_id": new_id,
                "old_id": old_id,
                "old_name": old_name,
                "reason": _RECT_REASON.format(old=old_name, new=new_name),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    for _old_name, new_name, _new_code in _RENAMES:
        new = bind.execute(
            sa.text("SELECT id FROM suppliers WHERE name = :n"),
            {"n": new_name},
        ).first()
        if new is None:
            continue
        new_id = new[0]

        bind.execute(
            sa.text(
                """
                UPDATE daily_inputs
                SET supplier_id          = (original_values->>'supplier_id')::bigint,
                    rectified_at         = NULL,
                    rectification_source = NULL,
                    rectification_reason = NULL,
                    original_values      = NULLIF(
                        original_values - 'supplier_id' - 'supplier_name',
                        '{}'::jsonb)
                WHERE supplier_id = :new_id
                """
            ),
            {"new_id": new_id},
        )
        bind.execute(
            sa.text("DELETE FROM suppliers WHERE id = :id"),
            {"id": new_id},
        )
