"""Per-PoS outbound eRSV + per-PoS GHG values

Revision ID: 0022_pos_outbound_ersv
Revises: 0021_logistics_downstream
Create Date: 2026-05-23

Cliente direction (2026-05-23): 1 outbound eRSV per Proof-of-Sustainability
document, NOT 1 per consignment. A Q3 2025 consignment with 20 PoS now mints
20 distinct outbound numbers (``CO/25/007`` … ``CO/25/026``). GHG values are
likewise carried per-PoS (one ISCC value triple per row).

Schema changes on ``consignment_pos``:
  + ``ersv_outbound_no`` TEXT, nullable, partial UNIQUE on (NOT NULL, deleted_at IS NULL)
  + ``ghg_ep``           NUMERIC(5,2), nullable  — processing emissions   gCO2eq/MJ
  + ``ghg_etd``          NUMERIC(5,2), nullable  — transport emissions    gCO2eq/MJ
  + ``ghg_total``        NUMERIC(5,2), nullable  — total                  gCO2eq/MJ
  + ``ghg_saving_pct``   NUMERIC(5,2), nullable  — saving vs fossil       percent
  + ``deleted_at``       TIMESTAMPTZ, nullable   — soft-delete column

``consignment.ersv_outbound_no`` is RETAINED as a nullable legacy column (no
new code reads it after this migration; backfill leaves it untouched).
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0022_pos_outbound_ersv"
down_revision = "0021_logistics_downstream"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # consignment_pos: new columns
    op.add_column(
        "consignment_pos",
        sa.Column("ersv_outbound_no", sa.Text(), nullable=True),
    )
    op.add_column(
        "consignment_pos",
        sa.Column("ghg_ep", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "consignment_pos",
        sa.Column("ghg_etd", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "consignment_pos",
        sa.Column("ghg_total", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "consignment_pos",
        sa.Column("ghg_saving_pct", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "consignment_pos",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Partial UNIQUE — only enforce uniqueness on active, allocated rows.
    op.create_index(
        "uq_consignment_pos_ersv_outbound_no_active",
        "consignment_pos",
        ["ersv_outbound_no"],
        unique=True,
        postgresql_where=sa.text(
            "ersv_outbound_no IS NOT NULL AND deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_consignment_pos_ersv_outbound_no_active",
        table_name="consignment_pos",
    )
    op.drop_column("consignment_pos", "deleted_at")
    op.drop_column("consignment_pos", "ghg_saving_pct")
    op.drop_column("consignment_pos", "ghg_total")
    op.drop_column("consignment_pos", "ghg_etd")
    op.drop_column("consignment_pos", "ghg_ep")
    op.drop_column("consignment_pos", "ersv_outbound_no")
