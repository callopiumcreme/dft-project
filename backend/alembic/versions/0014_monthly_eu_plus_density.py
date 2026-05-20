"""monthly densities for EU and PLUS + drop GENERATED litres columns

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-21

The EU and PLUS densities used so far were single project-wide
constants (0.7800 and 0.8560 kg/L) stored as one product_densities row
each, with effective_from 2025-01-01. The daily_production table had
two GENERATED ALWAYS columns hardcoded to those same constants:

    litres_eu   = eu_prod_kg   / 0.78
    litres_plus = plus_prod_kg / 0.856

Project owner now requires monthly densities for the Jan-Aug 2025
reporting period (supplied 2026-05-21):

    EU      Jan 0.756   Feb 0.762   Mar 0.782   Apr 0.778
            May 0.769   Jun 0.770   Jul 0.774   Aug 0.775

    PLUS    Jan 0.856   Feb 0.862   Mar 0.858   Apr 0.865
            May 0.868   Jun 0.853   Jul 0.871   Aug 0.859

Note PLUS Jan is unchanged at 0.856; EU Jan changes from 0.780 to
0.756 so the existing Jan EU row is UPDATED in place.

Schema changes
--------------
- daily_production: ALTER COLUMN litres_eu DROP EXPRESSION (and same
  for litres_plus) — converts the columns from GENERATED ALWAYS to
  plain numeric (PostgreSQL >= 12), keeping the existing stored
  values. Backfill then overwrites those values with the correct
  month-specific densities.
- New writes to daily_production no longer auto-populate litres_*.
  Application code (and any future migration) must compute and write
  them explicitly going forward, OR consume the canonical
  per-day litres from mv_mass_balance_daily which uses a LATERAL
  lookup against product_densities.

product_densities changes
-------------------------
- UPDATE the EU 2025-01-01 row from 0.7800 to 0.7560.
- INSERT seven monthly rows each for EU and PLUS (Feb-Aug 2025).
- PLUS 2025-01-01 row already at 0.8560 → no-op.

Materialized views
------------------
The MV LATERAL density lookups in mv_mass_balance_daily already pick
the latest product_densities row with effective_from <= the day in
question, so they automatically honour the new monthly densities once
the MVs are refreshed.
"""
from __future__ import annotations

from datetime import date

from alembic import op
from sqlalchemy import text


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


EU_DENSITIES = [
    (date(2025, 1, 1), "0.7560"),  # UPDATE existing (was 0.7800)
    (date(2025, 2, 1), "0.7620"),
    (date(2025, 3, 1), "0.7820"),
    (date(2025, 4, 1), "0.7780"),
    (date(2025, 5, 1), "0.7690"),
    (date(2025, 6, 1), "0.7700"),
    (date(2025, 7, 1), "0.7740"),
    (date(2025, 8, 1), "0.7750"),
]

PLUS_DENSITIES = [
    (date(2025, 1, 1), "0.8560"),  # no-op
    (date(2025, 2, 1), "0.8620"),
    (date(2025, 3, 1), "0.8580"),
    (date(2025, 4, 1), "0.8650"),
    (date(2025, 5, 1), "0.8680"),
    (date(2025, 6, 1), "0.8530"),
    (date(2025, 7, 1), "0.8710"),
    (date(2025, 8, 1), "0.8590"),
]


def upgrade() -> None:
    conn = op.get_bind()

    for product, rows in (("EU", EU_DENSITIES), ("PLUS", PLUS_DENSITIES)):
        for eff, dens in rows:
            conn.execute(
                text(
                    """
                    INSERT INTO product_densities
                      (product, density_kg_per_l, density_kg_per_m3, effective_from, source, notes)
                    VALUES
                      (:p, CAST(:d AS numeric), NULL, :eff,
                       'OisteBio process owner (2026-05-21)',
                       'Monthly liquid product density supplied for RTFO 8-month bundle')
                    ON CONFLICT (product, effective_from) DO UPDATE
                      SET density_kg_per_l = EXCLUDED.density_kg_per_l,
                          source = EXCLUDED.source,
                          notes = EXCLUDED.notes
                    """
                ),
                {"p": product, "d": dens, "eff": eff},
            )

    conn.execute(text("ALTER TABLE daily_production ALTER COLUMN litres_eu DROP EXPRESSION"))
    conn.execute(text("ALTER TABLE daily_production ALTER COLUMN litres_plus DROP EXPRESSION"))

    conn.execute(text(
        """
        WITH eu_d AS (
          SELECT effective_from, density_kg_per_l,
                 LEAD(effective_from) OVER (ORDER BY effective_from) AS next_from
          FROM product_densities WHERE product = 'EU'
        ),
        plus_d AS (
          SELECT effective_from, density_kg_per_l,
                 LEAD(effective_from) OVER (ORDER BY effective_from) AS next_from
          FROM product_densities WHERE product = 'PLUS'
        )
        UPDATE daily_production p
        SET
          litres_eu   = ROUND(p.eu_prod_kg   / eu_d.density_kg_per_l, 3),
          litres_plus = ROUND(p.plus_prod_kg / plus_d.density_kg_per_l, 3)
        FROM eu_d, plus_d
        WHERE p.prod_date >= eu_d.effective_from
          AND (eu_d.next_from IS NULL OR p.prod_date < eu_d.next_from)
          AND p.prod_date >= plus_d.effective_from
          AND (plus_d.next_from IS NULL OR p.prod_date < plus_d.next_from)
        """
    ))

    conn.execute(text("REFRESH MATERIALIZED VIEW mv_mass_balance_daily"))
    conn.execute(text("REFRESH MATERIALIZED VIEW mv_mass_balance_monthly"))


def downgrade() -> None:
    conn = op.get_bind()

    # Restore single-density rows.
    conn.execute(text("DELETE FROM product_densities WHERE product IN ('EU','PLUS') AND effective_from > '2025-01-01'"))
    conn.execute(text("UPDATE product_densities SET density_kg_per_l = 0.7800 WHERE product='EU' AND effective_from='2025-01-01'"))
    # PLUS 2025-01-01 stays at 0.8560.

    # Restore GENERATED ALWAYS columns. PostgreSQL does not allow
    # changing a plain column into GENERATED in place — drop + add.
    conn.execute(text("ALTER TABLE daily_production DROP COLUMN litres_eu"))
    conn.execute(text("ALTER TABLE daily_production DROP COLUMN litres_plus"))
    conn.execute(text(
        "ALTER TABLE daily_production ADD COLUMN litres_eu numeric GENERATED ALWAYS AS (eu_prod_kg / 0.78) STORED"
    ))
    conn.execute(text(
        "ALTER TABLE daily_production ADD COLUMN litres_plus numeric GENERATED ALWAYS AS (plus_prod_kg / 0.856) STORED"
    ))

    conn.execute(text("REFRESH MATERIALIZED VIEW mv_mass_balance_daily"))
    conn.execute(text("REFRESH MATERIALIZED VIEW mv_mass_balance_monthly"))
