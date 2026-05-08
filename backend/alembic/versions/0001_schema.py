"""initial schema v2 — split inputs/production, N:N junction, real-data shape

Revision ID: 0001
Revises:
Create Date: 2026-05-08

Schema design rationale (vedi docs/analisi-xlsx-2025.md):
- daily_inputs   : per-vehicle transactions (CAR/TRUCK/SPECIAL kg)
- daily_production: per-day aggregate (eu_prod, plus_prod, byproducts, output)
- supplier_certificates: junction N:N (cert CO222-00000026 shared 4 suppliers)
- c14_analysis TEXT (lab name / sample id / dates), non BOOLEAN
- is_aggregate flag for ≤5 TON pseudo-supplier
- is_placeholder flag for cert/contract placeholder ("-", "SD", "SELF DECL. ISCC")
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------- USERS ----------
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text()),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "role IN ('admin','operator','viewer','certifier')", name="users_role_check"
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ---------- SUPPLIERS ----------
    op.create_table(
        "suppliers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("code", sa.Text(), nullable=False, unique=True),
        sa.Column("country", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_aggregate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index("ix_suppliers_code", "suppliers", ["code"], unique=True)
    op.create_index(
        "ix_suppliers_active",
        "suppliers",
        ["active"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ---------- CERTIFICATES ----------
    op.create_table(
        "certificates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("cert_number", sa.Text(), nullable=False, unique=True),
        sa.Column("scheme", sa.Text(), nullable=False, server_default=sa.text("'ISCC EU'")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("issued_at", sa.Date()),
        sa.Column("expires_at", sa.Date()),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("document_url", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.CheckConstraint(
            "status IN ('active','expired','revoked','placeholder')", name="certificates_status_check"
        ),
    )
    op.create_index("ix_certificates_cert_number", "certificates", ["cert_number"], unique=True)
    op.create_index("ix_certificates_status", "certificates", ["status"])
    op.create_index("ix_certificates_expires_at", "certificates", ["expires_at"])

    # ---------- SUPPLIER_CERTIFICATES (N:N junction) ----------
    op.create_table(
        "supplier_certificates",
        sa.Column("supplier_id", sa.BigInteger(), nullable=False),
        sa.Column("certificate_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("supplier_id", "certificate_id"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["certificate_id"], ["certificates.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_supplier_certificates_cert", "supplier_certificates", ["certificate_id"])

    # ---------- CONTRACTS ----------
    op.create_table(
        "contracts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.Text(), nullable=False, unique=True),
        sa.Column("supplier_id", sa.BigInteger()),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("total_kg_committed", sa.Numeric(14, 3)),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_contracts_code", "contracts", ["code"], unique=True)
    op.create_index("ix_contracts_supplier_id", "contracts", ["supplier_id"])

    # ---------- DAILY_INPUTS (per-vehicle transactions) ----------
    op.create_table(
        "daily_inputs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("entry_time", sa.Time()),
        sa.Column("supplier_id", sa.BigInteger(), nullable=False),
        sa.Column("certificate_id", sa.BigInteger()),
        sa.Column("contract_id", sa.BigInteger()),
        sa.Column("ersv_number", sa.Text()),
        sa.Column("car_kg", sa.Numeric(14, 3), nullable=False, server_default=sa.text("0")),
        sa.Column("truck_kg", sa.Numeric(14, 3), nullable=False, server_default=sa.text("0")),
        sa.Column("special_kg", sa.Numeric(14, 3), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "total_input_kg",
            sa.Numeric(14, 3),
            sa.Computed("car_kg + truck_kg + special_kg", persisted=True),
            nullable=False,
        ),
        sa.Column("theor_veg_pct", sa.Numeric(5, 2)),
        sa.Column("manuf_veg_pct", sa.Numeric(5, 2)),
        sa.Column("c14_analysis", sa.Text()),
        sa.Column("c14_value", sa.Numeric(6, 3)),
        sa.Column("source_file", sa.Text()),
        sa.Column("source_row", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", sa.BigInteger()),
        sa.Column("updated_by", sa.BigInteger()),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["certificate_id"], ["certificates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("car_kg >= 0 AND truck_kg >= 0 AND special_kg >= 0", name="daily_inputs_kg_nonneg"),
    )
    op.create_index("ix_daily_inputs_entry_date", "daily_inputs", ["entry_date"])
    op.create_index("ix_daily_inputs_supplier_id", "daily_inputs", ["supplier_id"])
    op.create_index("ix_daily_inputs_certificate_id", "daily_inputs", ["certificate_id"])
    op.create_index("ix_daily_inputs_ersv_number", "daily_inputs", ["ersv_number"])
    op.create_index("ix_daily_inputs_date_supplier", "daily_inputs", ["entry_date", "supplier_id"])
    op.create_index(
        "ix_daily_inputs_active",
        "daily_inputs",
        ["entry_date"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ---------- DAILY_PRODUCTION (per-day aggregate) ----------
    op.create_table(
        "daily_production",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("prod_date", sa.Date(), nullable=False, unique=True),
        sa.Column("kg_to_production", sa.Numeric(14, 3)),
        sa.Column("eu_prod_kg", sa.Numeric(14, 3)),
        sa.Column("plus_prod_kg", sa.Numeric(14, 3)),
        sa.Column("carbon_black_kg", sa.Numeric(14, 3)),
        sa.Column("metal_scrap_kg", sa.Numeric(14, 3)),
        sa.Column("h2o_kg", sa.Numeric(14, 3)),
        sa.Column("gas_syngas_kg", sa.Numeric(14, 3)),
        sa.Column("losses_kg", sa.Numeric(14, 3)),
        sa.Column("output_eu_kg", sa.Numeric(14, 3)),
        sa.Column("contract_ref", sa.Text()),
        sa.Column("pos_number", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("source_file", sa.Text()),
        sa.Column("source_row", sa.Integer()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", sa.BigInteger()),
        sa.Column("updated_by", sa.BigInteger()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_daily_production_prod_date", "daily_production", ["prod_date"], unique=True)

    # ---------- AUDIT_LOG ----------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("old_values", sa.dialects.postgresql.JSONB()),
        sa.Column("new_values", sa.dialects.postgresql.JSONB()),
        sa.Column("changed_by", sa.BigInteger()),
        sa.Column("changed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "action IN ('insert','update','delete','soft_delete','restore')",
            name="audit_log_action_check",
        ),
    )
    op.create_index("ix_audit_log_table_record", "audit_log", ["table_name", "record_id"])
    op.create_index("ix_audit_log_changed_at", "audit_log", [sa.text("changed_at DESC")])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("daily_production")
    op.drop_table("daily_inputs")
    op.drop_table("contracts")
    op.drop_table("supplier_certificates")
    op.drop_table("certificates")
    op.drop_table("suppliers")
    op.drop_table("users")
