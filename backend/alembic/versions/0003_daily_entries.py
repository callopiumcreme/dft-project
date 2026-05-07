"""daily_entries: core mass balance table with GENERATED total_input_kg

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-07

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "daily_entries",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("entry_time", sa.Time(), nullable=True),
        # references
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("certificate_id", sa.Integer(), nullable=True),
        sa.Column("ersv_number", sa.String(50), nullable=True),
        # input weights
        sa.Column("car_kg", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("truck_kg", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=True),
        sa.Column("special_kg", sa.Numeric(10, 2), server_default=sa.text("0"), nullable=True),
        sa.Column(
            "total_input_kg",
            sa.Numeric(10, 2),
            sa.Computed(
                "COALESCE(car_kg,0) + COALESCE(truck_kg,0) + COALESCE(special_kg,0)",
                persisted=True,
            ),
            nullable=True,
        ),
        # veg %
        sa.Column("theor_veg_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("manuf_veg_pct", sa.Numeric(5, 2), nullable=True),
        # production
        sa.Column("kg_to_production", sa.Numeric(10, 2), nullable=True),
        sa.Column("eu_prod_kg", sa.Numeric(10, 2), nullable=True),
        sa.Column("plus_prod_kg", sa.Numeric(10, 2), nullable=True),
        # analysis
        sa.Column("c14_analysis", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.Column("c14_value", sa.Numeric(5, 2), nullable=True),
        # byproducts
        sa.Column("carbon_black_kg", sa.Numeric(10, 2), nullable=True),
        sa.Column("metal_scrap_kg", sa.Numeric(10, 2), nullable=True),
        # losses
        sa.Column("h2o_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("gas_syngas_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("losses_kg", sa.Numeric(10, 2), nullable=True),
        # output
        sa.Column("output_eu_kg", sa.Numeric(10, 2), nullable=True),
        sa.Column("contract_ref", sa.String(20), nullable=True),
        sa.Column("pos_number", sa.String(20), nullable=True),
        # audit
        sa.Column("source_file", sa.String(255), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(), nullable=True),
        # constraints
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name="fk_daily_entries_supplier_id"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], name="fk_daily_entries_contract_id"),
        sa.ForeignKeyConstraint(["certificate_id"], ["certificates.id"], name="fk_daily_entries_certificate_id"),
        sa.PrimaryKeyConstraint("id", name="pk_daily_entries"),
    )

    op.create_index("idx_daily_entries_date", "daily_entries", ["entry_date"])
    op.create_index("idx_daily_entries_supplier", "daily_entries", ["supplier_id"])
    op.create_index("idx_daily_entries_contract", "daily_entries", ["contract_id"])
    op.create_index("idx_daily_entries_deleted_at", "daily_entries", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("idx_daily_entries_deleted_at", table_name="daily_entries")
    op.drop_index("idx_daily_entries_contract", table_name="daily_entries")
    op.drop_index("idx_daily_entries_supplier", table_name="daily_entries")
    op.drop_index("idx_daily_entries_date", table_name="daily_entries")
    op.drop_table("daily_entries")
