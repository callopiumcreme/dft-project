"""add search indexes on FK and search fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07

"""
from __future__ import annotations

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # suppliers — non-unique search fields only (name covered by uq_suppliers_name)
    op.create_index("ix_suppliers_country", "suppliers", ["country"])
    op.create_index("ix_suppliers_active", "suppliers", ["active"])

    # contracts — FK + search fields (code covered by uq_contracts_code)
    op.create_index("ix_contracts_supplier_id", "contracts", ["supplier_id"])
    op.create_index("ix_contracts_start_date", "contracts", ["start_date"])
    op.create_index("ix_contracts_end_date", "contracts", ["end_date"])

    # certificates — FK + search fields (cert_number covered by uq_certificates_cert_number)
    op.create_index("ix_certificates_supplier_id", "certificates", ["supplier_id"])
    op.create_index("ix_certificates_scheme", "certificates", ["scheme"])
    op.create_index("ix_certificates_expires_at", "certificates", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_certificates_expires_at", table_name="certificates")
    op.drop_index("ix_certificates_scheme", table_name="certificates")
    op.drop_index("ix_certificates_supplier_id", table_name="certificates")
    op.drop_index("ix_contracts_end_date", table_name="contracts")
    op.drop_index("ix_contracts_start_date", table_name="contracts")
    op.drop_index("ix_contracts_supplier_id", table_name="contracts")
    op.drop_index("ix_suppliers_active", table_name="suppliers")
    op.drop_index("ix_suppliers_country", table_name="suppliers")
