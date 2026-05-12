"""drop orphan stock_markers table

stock_markers was created out-of-band (manual SQL or removed migration).
Not referenced by any model, parser, or report. Holds 18 orphan rows from
girardot_enero_2025.xlsx via the legacy parser. Drop to match codebase.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stock_markers CASCADE")


def downgrade() -> None:
    op.create_table(
        "stock_markers",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("marker_date", sa.Date(), nullable=False),
        sa.Column("stock_kg", sa.Numeric(14, 3), nullable=False),
        sa.Column("source_file", sa.Text(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("marker_date", "source_file"),
    )
