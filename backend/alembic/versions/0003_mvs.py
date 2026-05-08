"""materialized views for mass balance reporting

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08

Two MVs:
- mv_mass_balance_daily   : per prod_date — input vs production vs output, closure_diff_pct
- mv_mass_balance_monthly : aggregate (year, month) totals + closure

Both have UNIQUE INDEX so REFRESH MATERIALIZED VIEW CONCURRENTLY works.
NOTE: REFRESH CONCURRENTLY MUST run with AUTOCOMMIT engine (cannot be inside transaction).
"""

from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_mass_balance_daily AS
        SELECT
            COALESCE(p.prod_date, i.entry_date)              AS day,
            COALESCE(i.input_total_kg, 0)                    AS input_total_kg,
            p.kg_to_production                               AS kg_to_production,
            p.eu_prod_kg,
            p.plus_prod_kg,
            p.carbon_black_kg,
            p.metal_scrap_kg,
            p.h2o_kg,
            p.gas_syngas_kg,
            p.losses_kg,
            p.output_eu_kg,
            COALESCE(p.eu_prod_kg, 0)
              + COALESCE(p.plus_prod_kg, 0)
              + COALESCE(p.carbon_black_kg, 0)
              + COALESCE(p.metal_scrap_kg, 0)
              + COALESCE(p.h2o_kg, 0)
              + COALESCE(p.gas_syngas_kg, 0)
              + COALESCE(p.losses_kg, 0)                     AS output_total_kg,
            CASE
              WHEN COALESCE(i.input_total_kg, 0) > 0 THEN
                ROUND(
                  100.0 * (
                    COALESCE(p.eu_prod_kg, 0)
                    + COALESCE(p.plus_prod_kg, 0)
                    + COALESCE(p.carbon_black_kg, 0)
                    + COALESCE(p.metal_scrap_kg, 0)
                    + COALESCE(p.h2o_kg, 0)
                    + COALESCE(p.gas_syngas_kg, 0)
                    + COALESCE(p.losses_kg, 0)
                    - i.input_total_kg
                  ) / i.input_total_kg
                , 4)
              ELSE NULL
            END                                              AS closure_diff_pct
        FROM (
            SELECT entry_date, SUM(total_input_kg) AS input_total_kg
            FROM daily_inputs
            WHERE deleted_at IS NULL
            GROUP BY entry_date
        ) i
        FULL OUTER JOIN (
            SELECT *
            FROM daily_production
            WHERE deleted_at IS NULL
        ) p
        ON i.entry_date = p.prod_date;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_mv_mass_balance_daily_day "
        "ON mv_mass_balance_daily (day);"
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW mv_mass_balance_monthly AS
        SELECT
            DATE_TRUNC('month', day)::date                   AS month,
            SUM(input_total_kg)                              AS input_total_kg,
            SUM(COALESCE(eu_prod_kg, 0))                     AS eu_prod_kg,
            SUM(COALESCE(plus_prod_kg, 0))                   AS plus_prod_kg,
            SUM(COALESCE(carbon_black_kg, 0))                AS carbon_black_kg,
            SUM(COALESCE(metal_scrap_kg, 0))                 AS metal_scrap_kg,
            SUM(COALESCE(h2o_kg, 0))                         AS h2o_kg,
            SUM(COALESCE(gas_syngas_kg, 0))                  AS gas_syngas_kg,
            SUM(COALESCE(losses_kg, 0))                      AS losses_kg,
            SUM(COALESCE(output_eu_kg, 0))                   AS output_eu_kg,
            SUM(output_total_kg)                             AS output_total_kg,
            CASE
              WHEN SUM(input_total_kg) > 0 THEN
                ROUND(100.0 * (SUM(output_total_kg) - SUM(input_total_kg)) / SUM(input_total_kg), 4)
              ELSE NULL
            END                                              AS closure_diff_pct
        FROM mv_mass_balance_daily
        GROUP BY DATE_TRUNC('month', day);
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_mv_mass_balance_monthly_month "
        "ON mv_mass_balance_monthly (month);"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_mass_balance_monthly;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_mass_balance_daily;")
