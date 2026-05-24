"""Mass-balance ledger — append-only chain-of-custody event log

Revision ID: 0024_mass_balance_ledger
Revises: 0023_inland_shipment
Create Date: 2026-05-24

Implements the single source of truth for chain-of-custody as required
by docs/mass-balance-allocation-policy.md v1.0.

Each flow event (inbound feedstock, daily production, consignment
assignment, inland dispatch, ocean BL load, PoS issuance, UK delivery)
becomes exactly one row in ``mass_balance_ledger``. The table is
append-only with soft-delete: corrections are issued as new rows that
reference the superseded id via ``notes`` and ``corrects_id``.

Schema:
  - id                 BIGSERIAL PK
  - event_type         TEXT NOT NULL  -- CHECK in {inbound, production,
                                       consign_assign, inland_dispatch,
                                       bl_load, utb_transload, pos_issue,
                                       uk_delivery, correction}
  - event_date         DATE NOT NULL
  - kg_in              NUMERIC(14,3)  -- nullable: not all events have an in-side
  - kg_out             NUMERIC(14,3)  -- nullable: not all events have an out-side
  - ref_table          TEXT NOT NULL  -- source table name
  - ref_id             BIGINT NOT NULL  -- source row id
  - ref_doc_no         TEXT  -- eRSV / BL / PoS doc number when available
  - consignment_id     BIGINT FK consignment(id)  -- nullable for inbound/production
                                                  -- (not yet allocated)
  - prev_balance_kg    NUMERIC(14,3)  -- plant stock kg before this event
  - post_balance_kg    NUMERIC(14,3)  -- plant stock kg after this event
  - corrects_id        BIGINT FK mass_balance_ledger(id)  -- nullable correction ref
  - notes              TEXT
  - created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
  - created_by         BIGINT FK users(id)  -- nullable, app-level
  - deleted_at         TIMESTAMPTZ  -- soft-delete only, never hard delete

Indexes:
  - UNIQUE active (ref_table, ref_id, event_type) — one event per source row
  - INDEX (consignment_id, event_date) — per-consignment audit reports
  - INDEX (event_type, event_date) — global time queries
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0024_mass_balance_ledger"
down_revision = "0023_inland_shipment"
branch_labels = None
depends_on = None


_EVENT_TYPES = (
    "inbound",
    "production",
    "consign_assign",
    "inland_dispatch",
    "bl_load",
    "utb_transload",
    "pos_issue",
    "uk_delivery",
    "correction",
)


def upgrade() -> None:
    op.create_table(
        "mass_balance_ledger",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("kg_in", sa.Numeric(14, 3), nullable=True),
        sa.Column("kg_out", sa.Numeric(14, 3), nullable=True),
        sa.Column("ref_table", sa.Text(), nullable=False),
        sa.Column("ref_id", sa.BigInteger(), nullable=False),
        sa.Column("ref_doc_no", sa.Text(), nullable=True),
        sa.Column(
            "consignment_id",
            sa.BigInteger(),
            sa.ForeignKey("consignment.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("prev_balance_kg", sa.Numeric(14, 3), nullable=True),
        sa.Column("post_balance_kg", sa.Numeric(14, 3), nullable=True),
        sa.Column(
            "corrects_id",
            sa.BigInteger(),
            sa.ForeignKey("mass_balance_ledger.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Allowed event_type values
    op.create_check_constraint(
        "mass_balance_ledger_event_type_check",
        "mass_balance_ledger",
        sa.text(
            "event_type IN ("
            + ", ".join(f"'{t}'" for t in _EVENT_TYPES)
            + ")"
        ),
    )

    # kg_in / kg_out non-negative (NULL allowed)
    op.create_check_constraint(
        "mass_balance_ledger_kg_nonneg",
        "mass_balance_ledger",
        sa.text(
            "(kg_in IS NULL OR kg_in >= 0) AND "
            "(kg_out IS NULL OR kg_out >= 0)"
        ),
    )

    # At least one of kg_in / kg_out must be set
    op.create_check_constraint(
        "mass_balance_ledger_kg_at_least_one",
        "mass_balance_ledger",
        sa.text("kg_in IS NOT NULL OR kg_out IS NOT NULL"),
    )

    # Natural key — one event per source row + date (active rows only).
    # event_date is in the key so per-day events on composite-key tables
    # (e.g. consignment_production_link keyed on (consignment_id, prod_date))
    # can use ref_id=consignment_id and disambiguate by event_date.
    op.create_index(
        "uq_mass_balance_ledger_natural_active",
        "mass_balance_ledger",
        ["ref_table", "ref_id", "event_type", "event_date"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Per-consignment audit queries
    op.create_index(
        "ix_mass_balance_ledger_consignment_date",
        "mass_balance_ledger",
        ["consignment_id", "event_date"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Global time queries by event_type
    op.create_index(
        "ix_mass_balance_ledger_type_date",
        "mass_balance_ledger",
        ["event_type", "event_date"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mass_balance_ledger_type_date",
        table_name="mass_balance_ledger",
    )
    op.drop_index(
        "ix_mass_balance_ledger_consignment_date",
        table_name="mass_balance_ledger",
    )
    op.drop_index(
        "uq_mass_balance_ledger_natural_active",
        table_name="mass_balance_ledger",
    )
    op.drop_constraint(
        "mass_balance_ledger_kg_at_least_one",
        "mass_balance_ledger",
        type_="check",
    )
    op.drop_constraint(
        "mass_balance_ledger_kg_nonneg",
        "mass_balance_ledger",
        type_="check",
    )
    op.drop_constraint(
        "mass_balance_ledger_event_type_check",
        "mass_balance_ledger",
        type_="check",
    )
    op.drop_table("mass_balance_ledger")
