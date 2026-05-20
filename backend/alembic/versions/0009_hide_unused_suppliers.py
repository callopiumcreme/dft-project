"""hide 3 unused legacy suppliers (CIECOGRAS, ECODIESEL, SANIMAX)

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-20

Client directive (2026-05-20): hide three legacy supplier labels from
the UI. Cosmetic cleanup only — none of the three have active
daily_inputs rows:

  CIECOGRAS  — Feb-Aug movements already re-pointed to EFFICIEN
               TECHNOLOGY by migration 0008. Soft-deleted historical
               rows (parser-bug re-ingest 2026-05-12) stay on the
               CIECOGRAS supplier row but carry deleted_at IS NOT NULL
               so they are excluded from every report.

  SANIMAX    — Same story: Feb-Aug movements live on BOLDER
               INDUSTRIES (re-pointed by 0008); residual rows are
               soft-deleted parser-bug artefacts.

  ECODIESEL  — Never had active movements in the live dataset.

Soft delete (deleted_at = NOW(), active = false) — NOT a hard delete:
the suppliers row stays in place so the FK from soft-deleted
daily_inputs and from supplier_certificates remains valid and the
ISCC EU audit trail is preserved. The backend list endpoint
(``GET /suppliers``) filters ``deleted_at IS NULL`` unconditionally,
so the three labels disappear from /app/suppliers regardless of the
``active_only`` toggle. Mass-balance MVs aggregate by day (not by
supplier) so totals are unchanged.

Reversible — downgrade clears deleted_at + restores active=true on
exactly the three rows touched here.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_HIDE_NAMES = ("CIECOGRAS", "ECODIESEL", "SANIMAX")


def upgrade() -> None:
    bind = op.get_bind()
    res = bind.execute(
        sa.text(
            """
            UPDATE suppliers
            SET deleted_at = now(),
                active     = false
            WHERE name = ANY(CAST(:names AS text[]))
              AND deleted_at IS NULL
            RETURNING id, name
            """
        ),
        {"names": list(_HIDE_NAMES)},
    )
    hit = res.fetchall()
    if len(hit) != len(_HIDE_NAMES):
        found = {r[1] for r in hit}
        missing = [n for n in _HIDE_NAMES if n not in found]
        raise RuntimeError(
            f"Expected to soft-delete {_HIDE_NAMES}, "
            f"only updated {sorted(found)} (missing: {missing})"
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE suppliers
            SET deleted_at = NULL,
                active     = true
            WHERE name = ANY(CAST(:names AS text[]))
              AND deleted_at IS NOT NULL
            """
        ),
        {"names": list(_HIDE_NAMES)},
    )
