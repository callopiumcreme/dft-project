"""persist litres_eu and litres_plus as GENERATED columns on daily_production

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-15

Adds two GENERATED ALWAYS STORED columns to daily_production:

- litres_eu   NUMERIC GENERATED ALWAYS AS (eu_prod_kg   / 0.78)  STORED
- litres_plus NUMERIC GENERATED ALWAYS AS (plus_prod_kg / 0.856) STORED

Rationale (D2 = "persist", confirmed by client 2026-05-15):
- Per-row litres are now immutable for audit. If product densities change
  in the future, historical rows keep their original computed litres.
- This is independent of mv_mass_balance_daily / monthly, which compute
  litres via the time-effective LATERAL lookup on product_densities (0005).
  A follow-up story may drop the redundant litres calc in the MV — NOT
  done in this migration.

Constants used (frozen at migration time):
  EU   density = 0.78  kg/L  (see product_densities seed, 0005)
  PLUS density = 0.856 kg/L  (see product_densities seed, 0005)

Both columns are NULL when the source *_prod_kg column is NULL (Postgres
GENERATED with NULL operand yields NULL).

Hard rule: never write to litres_eu / litres_plus — they are GENERATED.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "daily_production",
        sa.Column(
            "litres_eu",
            sa.Numeric(),
            sa.Computed("eu_prod_kg / 0.78", persisted=True),
            nullable=True,
        ),
    )
    op.add_column(
        "daily_production",
        sa.Column(
            "litres_plus",
            sa.Numeric(),
            sa.Computed("plus_prod_kg / 0.856", persisted=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("daily_production", "litres_plus")
    op.drop_column("daily_production", "litres_eu")
