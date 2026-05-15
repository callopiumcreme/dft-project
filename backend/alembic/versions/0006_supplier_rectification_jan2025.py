"""supplier rectification audit columns on daily_inputs

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-15

Adds 5 nullable audit columns to daily_inputs to record post-hoc
rectifications of supplier-side data (eRSV corrections, weight
corrections, etc.) discovered during the Track A submission cycle for
Gen 2025.

Soft-rectification only — no hard delete. Existing rows stay NULL
(backfill not required). Columns:

- rectified_at           TIMESTAMPTZ NULL  — when row was rectified
- rectified_by           BIGINT NULL FK    — who applied rectification
- rectification_reason   TEXT NULL         — free-text justification
- rectification_source   VARCHAR(40) NULL  — supplier_letter |
                                              internal_audit |
                                              dft_request |
                                              other
- original_values        JSONB NULL        — pre-rectification snapshot

Index ix_daily_inputs_rectified_at on rectified_at (partial: WHERE NOT
NULL) for "show me all rectified rows" queries during ISCC EU audits.

Note: brief specified rectified_by as UUID; users.id is BIGINT in this
schema (see 0001_schema.py), so BIGINT FK is used to match. Pattern
mirrors existing created_by/updated_by on daily_inputs.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


_RECTIFICATION_SOURCES = (
    "supplier_letter",
    "internal_audit",
    "dft_request",
    "other",
)


def upgrade() -> None:
    op.add_column(
        "daily_inputs",
        sa.Column("rectified_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "daily_inputs",
        sa.Column(
            "rectified_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "daily_inputs",
        sa.Column("rectification_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "daily_inputs",
        sa.Column("rectification_source", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "daily_inputs",
        sa.Column("original_values", JSONB(), nullable=True),
    )

    # Enum-like check; allows NULL (no rectification yet).
    sources_csv = ", ".join(f"'{s}'" for s in _RECTIFICATION_SOURCES)
    op.create_check_constraint(
        "ck_daily_inputs_rectification_source",
        "daily_inputs",
        f"rectification_source IS NULL OR rectification_source IN ({sources_csv})",
    )

    # Partial index — most rows will be NULL forever; only index rectified ones.
    op.create_index(
        "ix_daily_inputs_rectified_at",
        "daily_inputs",
        ["rectified_at"],
        postgresql_where=sa.text("rectified_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_daily_inputs_rectified_at", table_name="daily_inputs")
    op.drop_constraint(
        "ck_daily_inputs_rectification_source",
        "daily_inputs",
        type_="check",
    )
    op.drop_column("daily_inputs", "original_values")
    op.drop_column("daily_inputs", "rectification_source")
    op.drop_column("daily_inputs", "rectification_reason")
    op.drop_column("daily_inputs", "rectified_by")
    op.drop_column("daily_inputs", "rectified_at")
