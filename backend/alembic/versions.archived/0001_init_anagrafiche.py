"""init anagrafiche: suppliers, contracts, certificates

Revision ID: 0001
Revises:
Create Date: 2026-05-07

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(2), server_default=sa.text("'CO'"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_suppliers"),
        sa.UniqueConstraint("name", name="uq_suppliers_name"),
        sa.UniqueConstraint("code", name="uq_suppliers_code"),
    )

    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("total_kg_committed", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name="fk_contracts_supplier_id"),
        sa.PrimaryKeyConstraint("id", name="pk_contracts"),
        sa.UniqueConstraint("code", name="uq_contracts_code"),
    )

    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cert_number", sa.String(50), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=False),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("scheme", sa.String(20), server_default=sa.text("'ISCC'"), nullable=False),
        sa.Column("document_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name="fk_certificates_supplier_id"),
        sa.PrimaryKeyConstraint("id", name="pk_certificates"),
        sa.UniqueConstraint("cert_number", name="uq_certificates_cert_number"),
    )


def downgrade() -> None:
    op.drop_table("certificates")
    op.drop_table("contracts")
    op.drop_table("suppliers")
