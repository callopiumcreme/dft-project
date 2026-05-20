"""add gas syngas monthly density + gas_syngas_m3 in mass-balance MVs

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-20

Adds support for storing volumetric (kg/m3) densities for gaseous
products alongside the existing volumetric (kg/L) densities used for
liquid products (EU, PLUS).

Schema changes
--------------
- `product_densities.density_kg_per_l` is relaxed to NULL (was NOT
  NULL). EU and PLUS rows keep their values.
- New nullable column `density_kg_per_m3 numeric(8,4)`.
- CHECK constraint replaces existing positivity check: exactly one of
  the two density columns must be populated AND positive.

Seed data
---------
Eight rows for product='GAS_SYNGAS' with monthly effective_from for
Jan-Aug 2025. Values supplied by project owner 2026-05-20:

  Jan 0.756   Feb 0.762   Mar 0.782   Apr 0.778
  May 0.744   Jun 0.751   Jul 0.778   Aug 0.774   (all kg/m3)

Materialized view changes
-------------------------
mv_mass_balance_daily gains `gas_syngas_m3` computed via a LATERAL
lookup against product_densities for product='GAS_SYNGAS' with the
same effective_from semantics already used by EU/PLUS litres lookups.

mv_mass_balance_monthly gains SUM(gas_syngas_m3) AS gas_syngas_m3.

Both MVs are DROP+CREATE'd to alter their column lists; their unique
indexes are recreated. Downgrade restores the prior MV bodies and
removes the schema additions.
"""
from __future__ import annotations

from datetime import date

from alembic import op
from sqlalchemy import text


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


GAS_DENSITIES = [
    (date(2025, 1, 1), "0.7560"),
    (date(2025, 2, 1), "0.7620"),
    (date(2025, 3, 1), "0.7820"),
    (date(2025, 4, 1), "0.7780"),
    (date(2025, 5, 1), "0.7440"),
    (date(2025, 6, 1), "0.7510"),
    (date(2025, 7, 1), "0.7780"),
    (date(2025, 8, 1), "0.7740"),
]


MV_DAILY_CREATE = """
CREATE MATERIALIZED VIEW mv_mass_balance_daily AS
SELECT
  COALESCE(p.prod_date, i.entry_date) AS day,
  COALESCE(i.input_total_kg, 0::numeric) AS input_total_kg,
  p.kg_to_production,
  p.eu_prod_kg,
  p.plus_prod_kg,
  p.carbon_black_kg,
  p.metal_scrap_kg,
  p.h2o_kg,
  p.gas_syngas_kg,
  p.losses_kg,
  p.output_eu_kg,
  round(p.eu_prod_kg / eu_d.density_kg_per_l, 3) AS eu_prod_litres,
  round(p.plus_prod_kg / plus_d.density_kg_per_l, 3) AS plus_prod_litres,
  round(
    COALESCE(p.eu_prod_kg / eu_d.density_kg_per_l, 0::numeric)
    + COALESCE(p.plus_prod_kg / plus_d.density_kg_per_l, 0::numeric)
  , 3) AS total_prod_litres,
  round(p.gas_syngas_kg / gas_d.density_kg_per_m3, 3) AS gas_syngas_m3,
  (COALESCE(p.eu_prod_kg, 0::numeric)
   + COALESCE(p.plus_prod_kg, 0::numeric)
   + COALESCE(p.carbon_black_kg, 0::numeric)
   + COALESCE(p.metal_scrap_kg, 0::numeric)
   + COALESCE(p.h2o_kg, 0::numeric)
   + COALESCE(p.gas_syngas_kg, 0::numeric)
   + COALESCE(p.losses_kg, 0::numeric)
  ) AS output_total_kg,
  CASE
    WHEN COALESCE(i.input_total_kg, 0::numeric) > 0::numeric THEN
      round(100.0 *
        ((COALESCE(p.eu_prod_kg, 0::numeric)
          + COALESCE(p.plus_prod_kg, 0::numeric)
          + COALESCE(p.carbon_black_kg, 0::numeric)
          + COALESCE(p.metal_scrap_kg, 0::numeric)
          + COALESCE(p.h2o_kg, 0::numeric)
          + COALESCE(p.gas_syngas_kg, 0::numeric)
          + COALESCE(p.losses_kg, 0::numeric)
         ) - i.input_total_kg
        ) / i.input_total_kg
      , 4)
    ELSE NULL::numeric
  END AS closure_diff_pct
FROM (
  SELECT entry_date, sum(total_input_kg) AS input_total_kg
  FROM daily_inputs WHERE deleted_at IS NULL
  GROUP BY entry_date
) i
FULL JOIN (
  SELECT * FROM daily_production WHERE deleted_at IS NULL
) p ON i.entry_date = p.prod_date
LEFT JOIN LATERAL (
  SELECT density_kg_per_l FROM product_densities
  WHERE product = 'EU'
    AND effective_from <= COALESCE(p.prod_date, i.entry_date)
  ORDER BY effective_from DESC LIMIT 1
) eu_d ON true
LEFT JOIN LATERAL (
  SELECT density_kg_per_l FROM product_densities
  WHERE product = 'PLUS'
    AND effective_from <= COALESCE(p.prod_date, i.entry_date)
  ORDER BY effective_from DESC LIMIT 1
) plus_d ON true
LEFT JOIN LATERAL (
  SELECT density_kg_per_m3 FROM product_densities
  WHERE product = 'GAS_SYNGAS'
    AND effective_from <= COALESCE(p.prod_date, i.entry_date)
  ORDER BY effective_from DESC LIMIT 1
) gas_d ON true;
"""

MV_MONTHLY_CREATE = """
CREATE MATERIALIZED VIEW mv_mass_balance_monthly AS
SELECT
  (date_trunc('month'::text, day::timestamptz))::date AS month,
  sum(input_total_kg) AS input_total_kg,
  sum(COALESCE(eu_prod_kg, 0::numeric)) AS eu_prod_kg,
  sum(COALESCE(plus_prod_kg, 0::numeric)) AS plus_prod_kg,
  sum(COALESCE(carbon_black_kg, 0::numeric)) AS carbon_black_kg,
  sum(COALESCE(metal_scrap_kg, 0::numeric)) AS metal_scrap_kg,
  sum(COALESCE(h2o_kg, 0::numeric)) AS h2o_kg,
  sum(COALESCE(gas_syngas_kg, 0::numeric)) AS gas_syngas_kg,
  sum(COALESCE(losses_kg, 0::numeric)) AS losses_kg,
  sum(COALESCE(output_eu_kg, 0::numeric)) AS output_eu_kg,
  sum(COALESCE(eu_prod_litres, 0::numeric)) AS eu_prod_litres,
  sum(COALESCE(plus_prod_litres, 0::numeric)) AS plus_prod_litres,
  sum(COALESCE(total_prod_litres, 0::numeric)) AS total_prod_litres,
  sum(COALESCE(gas_syngas_m3, 0::numeric)) AS gas_syngas_m3,
  sum(output_total_kg) AS output_total_kg,
  CASE
    WHEN sum(input_total_kg) > 0::numeric THEN
      round(100.0 * (sum(output_total_kg) - sum(input_total_kg)) / sum(input_total_kg), 4)
    ELSE NULL::numeric
  END AS closure_diff_pct
FROM mv_mass_balance_daily
GROUP BY (date_trunc('month'::text, day::timestamptz));
"""


MV_DAILY_PRIOR = """
CREATE MATERIALIZED VIEW mv_mass_balance_daily AS
SELECT
  COALESCE(p.prod_date, i.entry_date) AS day,
  COALESCE(i.input_total_kg, 0::numeric) AS input_total_kg,
  p.kg_to_production,
  p.eu_prod_kg,
  p.plus_prod_kg,
  p.carbon_black_kg,
  p.metal_scrap_kg,
  p.h2o_kg,
  p.gas_syngas_kg,
  p.losses_kg,
  p.output_eu_kg,
  round(p.eu_prod_kg / eu_d.density_kg_per_l, 3) AS eu_prod_litres,
  round(p.plus_prod_kg / plus_d.density_kg_per_l, 3) AS plus_prod_litres,
  round(
    COALESCE(p.eu_prod_kg / eu_d.density_kg_per_l, 0::numeric)
    + COALESCE(p.plus_prod_kg / plus_d.density_kg_per_l, 0::numeric)
  , 3) AS total_prod_litres,
  (COALESCE(p.eu_prod_kg, 0::numeric)
   + COALESCE(p.plus_prod_kg, 0::numeric)
   + COALESCE(p.carbon_black_kg, 0::numeric)
   + COALESCE(p.metal_scrap_kg, 0::numeric)
   + COALESCE(p.h2o_kg, 0::numeric)
   + COALESCE(p.gas_syngas_kg, 0::numeric)
   + COALESCE(p.losses_kg, 0::numeric)
  ) AS output_total_kg,
  CASE
    WHEN COALESCE(i.input_total_kg, 0::numeric) > 0::numeric THEN
      round(100.0 *
        ((COALESCE(p.eu_prod_kg, 0::numeric)
          + COALESCE(p.plus_prod_kg, 0::numeric)
          + COALESCE(p.carbon_black_kg, 0::numeric)
          + COALESCE(p.metal_scrap_kg, 0::numeric)
          + COALESCE(p.h2o_kg, 0::numeric)
          + COALESCE(p.gas_syngas_kg, 0::numeric)
          + COALESCE(p.losses_kg, 0::numeric)
         ) - i.input_total_kg
        ) / i.input_total_kg
      , 4)
    ELSE NULL::numeric
  END AS closure_diff_pct
FROM (
  SELECT entry_date, sum(total_input_kg) AS input_total_kg
  FROM daily_inputs WHERE deleted_at IS NULL
  GROUP BY entry_date
) i
FULL JOIN (
  SELECT * FROM daily_production WHERE deleted_at IS NULL
) p ON i.entry_date = p.prod_date
LEFT JOIN LATERAL (
  SELECT density_kg_per_l FROM product_densities
  WHERE product = 'EU'
    AND effective_from <= COALESCE(p.prod_date, i.entry_date)
  ORDER BY effective_from DESC LIMIT 1
) eu_d ON true
LEFT JOIN LATERAL (
  SELECT density_kg_per_l FROM product_densities
  WHERE product = 'PLUS'
    AND effective_from <= COALESCE(p.prod_date, i.entry_date)
  ORDER BY effective_from DESC LIMIT 1
) plus_d ON true;
"""

MV_MONTHLY_PRIOR = """
CREATE MATERIALIZED VIEW mv_mass_balance_monthly AS
SELECT
  (date_trunc('month'::text, day::timestamptz))::date AS month,
  sum(input_total_kg) AS input_total_kg,
  sum(COALESCE(eu_prod_kg, 0::numeric)) AS eu_prod_kg,
  sum(COALESCE(plus_prod_kg, 0::numeric)) AS plus_prod_kg,
  sum(COALESCE(carbon_black_kg, 0::numeric)) AS carbon_black_kg,
  sum(COALESCE(metal_scrap_kg, 0::numeric)) AS metal_scrap_kg,
  sum(COALESCE(h2o_kg, 0::numeric)) AS h2o_kg,
  sum(COALESCE(gas_syngas_kg, 0::numeric)) AS gas_syngas_kg,
  sum(COALESCE(losses_kg, 0::numeric)) AS losses_kg,
  sum(COALESCE(output_eu_kg, 0::numeric)) AS output_eu_kg,
  sum(COALESCE(eu_prod_litres, 0::numeric)) AS eu_prod_litres,
  sum(COALESCE(plus_prod_litres, 0::numeric)) AS plus_prod_litres,
  sum(COALESCE(total_prod_litres, 0::numeric)) AS total_prod_litres,
  sum(output_total_kg) AS output_total_kg,
  CASE
    WHEN sum(input_total_kg) > 0::numeric THEN
      round(100.0 * (sum(output_total_kg) - sum(input_total_kg)) / sum(input_total_kg), 4)
    ELSE NULL::numeric
  END AS closure_diff_pct
FROM mv_mass_balance_daily
GROUP BY (date_trunc('month'::text, day::timestamptz));
"""


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("ALTER TABLE product_densities ALTER COLUMN density_kg_per_l DROP NOT NULL"))
    conn.execute(text("ALTER TABLE product_densities ADD COLUMN density_kg_per_m3 numeric(8,4)"))
    conn.execute(text("ALTER TABLE product_densities DROP CONSTRAINT ck_product_densities_positive"))
    conn.execute(text("ALTER TABLE product_densities DROP CONSTRAINT ck_product_densities_product"))
    conn.execute(text(
        """
        ALTER TABLE product_densities ADD CONSTRAINT ck_product_densities_product CHECK (
          product = ANY (ARRAY['EU'::text, 'PLUS'::text, 'GAS_SYNGAS'::text])
        )
        """
    ))
    conn.execute(text(
        """
        ALTER TABLE product_densities ADD CONSTRAINT ck_product_densities_one_unit CHECK (
          (density_kg_per_l IS NOT NULL AND density_kg_per_l > 0 AND density_kg_per_m3 IS NULL)
          OR
          (density_kg_per_m3 IS NOT NULL AND density_kg_per_m3 > 0 AND density_kg_per_l IS NULL)
        )
        """
    ))

    for effective_from, density in GAS_DENSITIES:
        conn.execute(
            text(
                """
                INSERT INTO product_densities
                  (product, density_kg_per_l, density_kg_per_m3, effective_from, source, notes)
                VALUES
                  ('GAS_SYNGAS', NULL, CAST(:d AS numeric), :eff,
                   'OisteBio process owner (2026-05-20)',
                   'Monthly gas syngas density supplied for RTFO 8-month bundle')
                """
            ),
            {"d": density, "eff": effective_from},
        )

    conn.execute(text("DROP MATERIALIZED VIEW mv_mass_balance_monthly"))
    conn.execute(text("DROP MATERIALIZED VIEW mv_mass_balance_daily"))
    conn.execute(text(MV_DAILY_CREATE))
    conn.execute(text(MV_MONTHLY_CREATE))
    conn.execute(text(
        "CREATE UNIQUE INDEX ux_mv_mass_balance_daily_day ON mv_mass_balance_daily (day)"
    ))
    conn.execute(text(
        "CREATE UNIQUE INDEX ux_mv_mass_balance_monthly_month ON mv_mass_balance_monthly (month)"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("DROP MATERIALIZED VIEW mv_mass_balance_monthly"))
    conn.execute(text("DROP MATERIALIZED VIEW mv_mass_balance_daily"))
    conn.execute(text(MV_DAILY_PRIOR))
    conn.execute(text(MV_MONTHLY_PRIOR))
    conn.execute(text(
        "CREATE UNIQUE INDEX ux_mv_mass_balance_daily_day ON mv_mass_balance_daily (day)"
    ))
    conn.execute(text(
        "CREATE UNIQUE INDEX ux_mv_mass_balance_monthly_month ON mv_mass_balance_monthly (month)"
    ))

    conn.execute(text("DELETE FROM product_densities WHERE product = 'GAS_SYNGAS'"))
    conn.execute(text("ALTER TABLE product_densities DROP CONSTRAINT ck_product_densities_one_unit"))
    conn.execute(text("ALTER TABLE product_densities DROP CONSTRAINT ck_product_densities_product"))
    conn.execute(text(
        """
        ALTER TABLE product_densities ADD CONSTRAINT ck_product_densities_product CHECK (
          product = ANY (ARRAY['EU'::text, 'PLUS'::text])
        )
        """
    ))
    conn.execute(text("ALTER TABLE product_densities DROP COLUMN density_kg_per_m3"))
    conn.execute(text("ALTER TABLE product_densities ALTER COLUMN density_kg_per_l SET NOT NULL"))
    conn.execute(text(
        "ALTER TABLE product_densities ADD CONSTRAINT ck_product_densities_positive CHECK (density_kg_per_l > 0)"
    ))
