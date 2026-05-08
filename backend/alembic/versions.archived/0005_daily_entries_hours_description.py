"""daily_entries: add hours and description columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-07

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("daily_entries", sa.Column("hours", sa.Numeric(5, 2), nullable=True))
    op.add_column("daily_entries", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("daily_entries", "description")
    op.drop_column("daily_entries", "hours")
