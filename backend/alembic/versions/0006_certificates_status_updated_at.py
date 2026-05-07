"""certificates: add status + updated_at

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-07

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str = "0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "certificates",
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
    )
    op.add_column(
        "certificates",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_certificates_status",
        "certificates",
        "status IN ('active', 'expired', 'suspended')",
    )
    op.create_index("ix_certificates_status", "certificates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_certificates_status", table_name="certificates")
    op.drop_constraint("ck_certificates_status", "certificates", type_="check")
    op.drop_column("certificates", "updated_at")
    op.drop_column("certificates", "status")
