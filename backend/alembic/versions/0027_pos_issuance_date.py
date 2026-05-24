"""Add issuance_date column on consignment_pos.

The PoS document carries its own ``Date of issuance of the PoS`` (or
``Date of Issuance of the PoS:`` on the older V3.1 template). That date is
the legal moment custody of the EU oil transfers to Crown Oil — distinct
from ``consignment.delivered_uk`` (physical arrival in the UK) and from
``consignment_pos.created_at`` (DB insert timestamp).

For the warehouse / mass-balance ledger, EU oil discharge should debit on
issuance_date, not on delivered_uk. This migration only adds the column;
``scripts/backfill_pos_issuance.py`` parses the PDFs and populates it, and
``scripts/backfill_warehouse.py`` is updated to read from this column when
emitting ``event_type='pos_issue'`` ledger rows.

Nullable on purpose: legacy rows without a parseable PDF stay NULL and are
skipped by the warehouse backfill (they remain visible but do not generate
a discharge event). The CHECK constraint for event_type already allows
``pos_issue`` since 0026, so no constraint changes are needed.

Revision ID: 0027_pos_issuance_date
Revises: 0026_warehouse
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0027_pos_issuance_date"
down_revision = "0026_warehouse"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consignment_pos",
        sa.Column("issuance_date", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_consignment_pos_issuance_date",
        "consignment_pos",
        ["issuance_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_consignment_pos_issuance_date",
        table_name="consignment_pos",
    )
    op.drop_column("consignment_pos", "issuance_date")
