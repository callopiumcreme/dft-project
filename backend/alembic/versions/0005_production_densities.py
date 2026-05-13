"""product densities lookup + litres in mass-balance MVs

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-13

Adds:
- product_densities table — time-effective density lookup with provenance
  (audit-grade; regulator can ask "where did 0.780 come from?" -> source)
- Seed: EU=0.780 kg/L, PLUS=0.856 kg/L, effective_from=2025-01-01,
  source='EAD (Andrea Olga, OisteBio)'
- Rebuild mv_mass_balance_daily / mv_mass_balance_monthly to include
  eu_prod_litres, plus_prod_litres, total_prod_litres (per-day densities
  via LATERAL join — supports density changes over time)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_densities",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("product", sa.Text(), nullable=False),
        sa.Column("density_kg_per_l", sa.Numeric(6, 4), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("density_kg_per_l > 0", name="ck_product_densities_positive"),
        sa.CheckConstraint(
            "product IN ('EU', 'PLUS')", name="ck_product_densities_product"
        ),
        sa.UniqueConstraint("product", "effective_from", name="uq_product_densities"),
    )

    op.execute(
        """
        INSERT INTO product_densities (product, density_kg_per_l, effective_from, source, notes)
        VALUES
          ('EU',   0.7800, '2025-01-01', 'EAD (Andrea Olga, OisteBio)',
           'Density confirmed 2026-05-13 via WhatsApp from EAD reference'),
          ('PLUS', 0.8560, '2025-01-01', 'EAD (Andrea Olga, OisteBio)',
           'Density confirmed 2026-05-13 via WhatsApp from EAD reference');
        """
    )

    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_mass_balance_monthly;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_mass_balance_daily;")

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
            ROUND(p.eu_prod_kg   / eu_d.density_kg_per_l,   3) AS eu_prod_litres,
            ROUND(p.plus_prod_kg / plus_d.density_kg_per_l, 3) AS plus_prod_litres,
            ROUND(
                COALESCE(p.eu_prod_kg / eu_d.density_kg_per_l, 0)
              + COALESCE(p.plus_prod_kg / plus_d.density_kg_per_l, 0)
            , 3)                                              AS total_prod_litres,
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
        ON i.entry_date = p.prod_date
        LEFT JOIN LATERAL (
            SELECT density_kg_per_l
            FROM product_densities
            WHERE product = 'EU'
              AND effective_from <= COALESCE(p.prod_date, i.entry_date)
            ORDER BY effective_from DESC
            LIMIT 1
        ) eu_d ON true
        LEFT JOIN LATERAL (
            SELECT density_kg_per_l
            FROM product_densities
            WHERE product = 'PLUS'
              AND effective_from <= COALESCE(p.prod_date, i.entry_date)
            ORDER BY effective_from DESC
            LIMIT 1
        ) plus_d ON true;
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
            SUM(COALESCE(eu_prod_litres, 0))                 AS eu_prod_litres,
            SUM(COALESCE(plus_prod_litres, 0))               AS plus_prod_litres,
            SUM(COALESCE(total_prod_litres, 0))              AS total_prod_litres,
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

    op.drop_table("product_densities")
