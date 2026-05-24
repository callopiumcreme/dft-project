"""Warehouse inventory — byproducts + per-product stock views

Revision ID: 0026_warehouse
Revises: 0025_v_chain_summary
Create Date: 2026-05-24

Extends the mass-balance ledger to track non-EU-oil outputs of the
Girardot plant (Plus-grade pyrolysis oil, carbon black, metal scrap,
syngas, water vent) and adds first-class warehouse views:

  - mass_balance_ledger.event_type: adds byproduct_sale, syngas_burn,
    h2o_vent, opening to the allowed set
  - mass_balance_ledger.product_kind: NEW column, defaults to 'eu_oil'
    so existing ledger rows remain valid without backfill
  - byproduct_buyer: lightweight buyer table for non-EU streams
    (separate from the main supplier/buyer model since these are
    one-off industrial offtakes, not RTFO-bundle counterparties)
  - byproduct_sale: per-sale invoice rows feeding the ledger via
    event_type='byproduct_sale'
  - v_warehouse_stock: per product_kind on-hand / cumulative
    produced / cumulative dispatched (derived from ledger)
  - v_warehouse_recent_movements: last 100 ledger rows for the
    /app/warehouse dashboard widget

All tables follow project soft-delete convention (deleted_at column,
partial unique indexes WHERE deleted_at IS NULL). Views are fully
derived — drop/recreate on schema change without data migration.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0026_warehouse"
down_revision = "0025_v_chain_summary"
branch_labels = None
depends_on = None


_EVENT_TYPES_NEW = (
    "inbound",
    "production",
    "consign_assign",
    "inland_dispatch",
    "bl_load",
    "utb_transload",
    "pos_issue",
    "uk_delivery",
    "correction",
    "opening",
    "byproduct_sale",
    "syngas_burn",
    "h2o_vent",
)

_EVENT_TYPES_OLD = (
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

_PRODUCT_KINDS = (
    "eu_oil",
    "plus_oil",
    "carbon_black",
    "metal_scrap",
    "syngas",
    "h2o",
)

_BYPRODUCT_SALE_KINDS = (
    "plus_oil",
    "carbon_black",
    "metal_scrap",
)


_CREATE_V_WAREHOUSE_STOCK = """
CREATE OR REPLACE VIEW v_warehouse_stock AS
SELECT
  product_kind,
  COALESCE(SUM(kg_in), 0) - COALESCE(SUM(kg_out), 0) AS stock_kg,
  COALESCE(SUM(kg_in), 0)                            AS produced_total_kg,
  COALESCE(SUM(kg_out), 0)                           AS dispatched_total_kg,
  MAX(event_date)                                    AS last_movement_at
FROM mass_balance_ledger
WHERE deleted_at IS NULL
GROUP BY product_kind;
"""


_CREATE_V_WAREHOUSE_RECENT = """
CREATE OR REPLACE VIEW v_warehouse_recent_movements AS
SELECT
  id,
  event_date,
  event_type,
  product_kind,
  kg_in,
  kg_out,
  post_balance_kg,
  ref_doc_no,
  consignment_id,
  notes
FROM mass_balance_ledger
WHERE deleted_at IS NULL
ORDER BY event_date DESC, id DESC
LIMIT 100;
"""


def upgrade() -> None:
    # 1. Extend allowed event_type values on the ledger
    op.drop_constraint(
        "mass_balance_ledger_event_type_check",
        "mass_balance_ledger",
        type_="check",
    )
    op.create_check_constraint(
        "mass_balance_ledger_event_type_check",
        "mass_balance_ledger",
        sa.text(
            "event_type IN ("
            + ", ".join(f"'{t}'" for t in _EVENT_TYPES_NEW)
            + ")"
        ),
    )

    # 2. Add product_kind column with default 'eu_oil' so existing rows stay valid
    op.add_column(
        "mass_balance_ledger",
        sa.Column(
            "product_kind",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'eu_oil'"),
        ),
    )
    op.create_check_constraint(
        "mass_balance_ledger_product_kind_check",
        "mass_balance_ledger",
        sa.text(
            "product_kind IN ("
            + ", ".join(f"'{k}'" for k in _PRODUCT_KINDS)
            + ")"
        ),
    )

    # 3. byproduct_buyer — lightweight counterparty table for non-EU streams
    op.create_table(
        "byproduct_buyer",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("vat", sa.Text(), nullable=True),
        sa.Column("contact", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Unique active name (partial index — soft-delete friendly)
    op.create_index(
        "uq_byproduct_buyer_name_active",
        "byproduct_buyer",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 4. byproduct_sale — invoice rows for plus_oil / carbon_black / metal_scrap
    op.create_table(
        "byproduct_sale",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True
        ),
        sa.Column("product_kind", sa.Text(), nullable=False),
        sa.Column(
            "buyer_id",
            sa.BigInteger(),
            sa.ForeignKey("byproduct_buyer.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("kg_net", sa.Numeric(14, 3), nullable=False),
        sa.Column("invoice_no", sa.Text(), nullable=True),
        sa.Column("price_eur", sa.Numeric(14, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_check_constraint(
        "byproduct_sale_product_kind_check",
        "byproduct_sale",
        sa.text(
            "product_kind IN ("
            + ", ".join(f"'{k}'" for k in _BYPRODUCT_SALE_KINDS)
            + ")"
        ),
    )

    op.create_check_constraint(
        "byproduct_sale_kg_net_positive",
        "byproduct_sale",
        sa.text("kg_net > 0"),
    )

    op.create_index(
        "ix_byproduct_sale_date_kind",
        "byproduct_sale",
        ["sale_date", "product_kind"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 5. v_warehouse_stock — per-product on-hand + cumulative totals
    op.execute(_CREATE_V_WAREHOUSE_STOCK)

    # 6. v_warehouse_recent_movements — last 100 ledger rows
    op.execute(_CREATE_V_WAREHOUSE_RECENT)


def downgrade() -> None:
    # Reverse order — views first, then tables, then column, then constraint
    op.execute("DROP VIEW IF EXISTS v_warehouse_recent_movements")
    op.execute("DROP VIEW IF EXISTS v_warehouse_stock")

    op.drop_index(
        "ix_byproduct_sale_date_kind",
        table_name="byproduct_sale",
    )
    op.drop_constraint(
        "byproduct_sale_kg_net_positive",
        "byproduct_sale",
        type_="check",
    )
    op.drop_constraint(
        "byproduct_sale_product_kind_check",
        "byproduct_sale",
        type_="check",
    )
    op.drop_table("byproduct_sale")

    op.drop_index(
        "uq_byproduct_buyer_name_active",
        table_name="byproduct_buyer",
    )
    op.drop_table("byproduct_buyer")

    op.drop_constraint(
        "mass_balance_ledger_product_kind_check",
        "mass_balance_ledger",
        type_="check",
    )
    op.drop_column("mass_balance_ledger", "product_kind")

    # Restore original event_type CHECK (pre-0026 set)
    op.drop_constraint(
        "mass_balance_ledger_event_type_check",
        "mass_balance_ledger",
        type_="check",
    )
    op.create_check_constraint(
        "mass_balance_ledger_event_type_check",
        "mass_balance_ledger",
        sa.text(
            "event_type IN ("
            + ", ".join(f"'{t}'" for t in _EVENT_TYPES_OLD)
            + ")"
        ),
    )
