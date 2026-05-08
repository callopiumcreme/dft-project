"""materialized views: mv_mass_balance_daily, mv_mass_balance_monthly

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-07

"""
from __future__ import annotations

from alembic import op

revision: str = "0008"
down_revision: str = "0007"
branch_labels: str | None = None
depends_on: str | None = None

_CREATE_DAILY = """
CREATE MATERIALIZED VIEW mv_mass_balance_daily AS
SELECT
  entry_date,
  COUNT(*)                                                            AS entries_count,
  SUM(total_input_kg)                                                 AS input_kg,
  SUM(eu_prod_kg)                                                     AS eu_prod_kg,
  SUM(plus_prod_kg)                                                   AS plus_prod_kg,
  SUM(output_eu_kg)                                                   AS output_eu_kg,
  SUM(carbon_black_kg)                                                AS carbon_black_kg,
  SUM(metal_scrap_kg)                                                 AS metal_scrap_kg,
  SUM(losses_kg)                                                      AS losses_kg,
  AVG(theor_veg_pct)                                                  AS avg_theor_veg_pct,
  AVG(manuf_veg_pct)                                                  AS avg_manuf_veg_pct,
  (
    COALESCE(SUM(eu_prod_kg), 0) +
    COALESCE(SUM(plus_prod_kg), 0) +
    COALESCE(SUM(carbon_black_kg), 0) +
    COALESCE(SUM(metal_scrap_kg), 0) +
    COALESCE(SUM(losses_kg), 0)
  )                                                                   AS total_output_kg,
  (
    COALESCE(SUM(total_input_kg), 0) - (
      COALESCE(SUM(eu_prod_kg), 0) +
      COALESCE(SUM(plus_prod_kg), 0) +
      COALESCE(SUM(carbon_black_kg), 0) +
      COALESCE(SUM(metal_scrap_kg), 0) +
      COALESCE(SUM(losses_kg), 0)
    )
  )                                                                   AS closure_diff_kg
FROM daily_entries
WHERE deleted_at IS NULL
GROUP BY entry_date
WITH DATA;
"""

_CREATE_MONTHLY = """
CREATE MATERIALIZED VIEW mv_mass_balance_monthly AS
SELECT
  date_trunc('month', entry_date)  AS month,
  supplier_id,
  SUM(total_input_kg)              AS input_kg,
  SUM(eu_prod_kg)                  AS eu_prod_kg,
  SUM(plus_prod_kg)                AS plus_prod_kg,
  SUM(output_eu_kg)                AS output_eu_kg
FROM daily_entries
WHERE deleted_at IS NULL
GROUP BY date_trunc('month', entry_date), supplier_id
WITH DATA;
"""

_CREATE_REFRESH_FN = """
CREATE OR REPLACE FUNCTION refresh_mass_balance_views()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY mv_mass_balance_daily;
  REFRESH MATERIALIZED VIEW CONCURRENTLY mv_mass_balance_monthly;
END;
$$;
"""

# CONCURRENTLY requires a unique index on the view
_CREATE_DAILY_UNIQUE_IDX = (
    "CREATE UNIQUE INDEX uq_mv_mass_balance_daily_date "
    "ON mv_mass_balance_daily (entry_date);"
)
_CREATE_MONTHLY_UNIQUE_IDX = (
    "CREATE UNIQUE INDEX uq_mv_mass_balance_monthly_month_supplier "
    "ON mv_mass_balance_monthly (month, supplier_id);"
)


def upgrade() -> None:
    op.execute(_CREATE_DAILY)
    op.execute(_CREATE_MONTHLY)
    op.execute(_CREATE_DAILY_UNIQUE_IDX)
    op.execute(_CREATE_MONTHLY_UNIQUE_IDX)
    op.execute(_CREATE_REFRESH_FN)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS refresh_mass_balance_views();")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_mass_balance_monthly;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_mass_balance_daily;")
