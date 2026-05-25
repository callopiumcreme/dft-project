"""Warehouse view — split produced into current-year YTD vs prior-year opening

Revision ID: 0029_warehouse_ytd
Revises: 0028_consignment_pos_soft_delete_unique
Create Date: 2026-05-25

Background
----------
Before this migration ``v_warehouse_stock.produced_total_kg`` aggregated the
*entire* ledger (no date filter), but the landing card labelled it
"Produced YTD" — misleading because the figure includes the opening
balance row (event_type='opening', year 2024) for every stockable
product. Operators reading the dashboard could not distinguish
real-year production from carry-over.

Change
------
Extend ``v_warehouse_stock`` with two extra columns:

  - ``produced_ytd_kg``      : SUM(kg_in) where event_date is in the
                               most-recent operational year present in
                               the ledger
  - ``opening_balance_kg``   : SUM(kg_in) where event_date is in any
                               *prior* year (i.e. carry-over)

``produced_total_kg`` is kept for backwards compat — it stays equal to
``produced_ytd_kg + opening_balance_kg``.

The "operational year" is derived dynamically as
``MAX(EXTRACT(YEAR FROM event_date))`` over all non-deleted ledger
rows, so the view auto-rolls when 2026 production starts hitting the
ledger.
"""

from __future__ import annotations

from alembic import op


revision = "0029_warehouse_ytd"
down_revision = "0028_consignment_pos_softdel"
branch_labels = None
depends_on = None


_CREATE_V_WAREHOUSE_STOCK_NEW = """
CREATE OR REPLACE VIEW v_warehouse_stock AS
WITH boundary AS (
  SELECT COALESCE(MAX(EXTRACT(YEAR FROM event_date))::int, EXTRACT(YEAR FROM CURRENT_DATE)::int) AS yr
  FROM mass_balance_ledger
  WHERE deleted_at IS NULL
)
SELECT
  l.product_kind,
  COALESCE(SUM(l.kg_in), 0) - COALESCE(SUM(l.kg_out), 0) AS stock_kg,
  COALESCE(SUM(l.kg_in), 0)                              AS produced_total_kg,
  COALESCE(SUM(l.kg_out), 0)                             AS dispatched_total_kg,
  MAX(l.event_date)                                       AS last_movement_at,
  COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM l.event_date) = b.yr THEN l.kg_in END), 0) AS produced_ytd_kg,
  COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM l.event_date) < b.yr THEN l.kg_in END), 0) AS opening_balance_kg
FROM mass_balance_ledger l
CROSS JOIN boundary b
WHERE l.deleted_at IS NULL
GROUP BY l.product_kind, b.yr;
"""


_CREATE_V_WAREHOUSE_STOCK_OLD = """
CREATE OR REPLACE VIEW v_warehouse_stock AS
SELECT
  product_kind,
  COALESCE(SUM(kg_in), 0) - COALESCE(SUM(kg_out), 0) AS stock_kg,
  COALESCE(SUM(kg_in), 0)                            AS produced_total_kg,
  COALESCE(SUM(kg_out), 0)                           AS dispatched_total_kg,
  MAX(event_date)                                    AS last_movement_at
FROM mass_balance_ledger
WHERE deleted_at IS NULL
GROUP BY product_kind;
"""


def upgrade() -> None:
    op.execute(_CREATE_V_WAREHOUSE_STOCK_NEW)


def downgrade() -> None:
    op.execute(_CREATE_V_WAREHOUSE_STOCK_OLD)
