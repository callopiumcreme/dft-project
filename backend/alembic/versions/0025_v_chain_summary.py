"""SQL view ``v_chain_summary`` — per-consignment chain-of-custody totals

Revision ID: 0025_v_chain_summary
Revises: 0024_mass_balance_ledger
Create Date: 2026-05-24

Read-only aggregate over consignment + upstream (daily_inputs,
daily_production) + midstream (inland_shipment, shipment_leg) +
downstream (consignment_pos). Powers the chain-of-custody widget on
``/app/logistics/[id]`` and the audit-pack export endpoint.

The view is fully derived from existing tables; no separate storage. If
the upstream rule changes, drop and recreate without data migration.
"""
from __future__ import annotations

from alembic import op

revision = "0025_v_chain_summary"
down_revision = "0024_mass_balance_ledger"
branch_labels = None
depends_on = None


_CREATE_VIEW = """
CREATE OR REPLACE VIEW v_chain_summary AS
SELECT
    c.id                                AS consignment_id,
    c.code                              AS consignment_code,
    c.status,
    c.product_grade,
    c.total_kg                          AS consignment_kg,
    c.prod_date_from,
    c.prod_date_to,

    -- Upstream: inbound ELT feedstock during consignment window
    (SELECT COUNT(DISTINCT di.ersv_number)
       FROM daily_inputs di
      WHERE di.deleted_at IS NULL
        AND di.entry_date BETWEEN c.prod_date_from AND c.prod_date_to
        AND di.ersv_number IS NOT NULL
    )                                   AS inbound_ersv_count,

    (SELECT COUNT(DISTINCT di.supplier_id)
       FROM daily_inputs di
      WHERE di.deleted_at IS NULL
        AND di.entry_date BETWEEN c.prod_date_from AND c.prod_date_to
    )                                   AS inbound_supplier_count,

    (SELECT COALESCE(SUM(di.total_input_kg), 0)
       FROM daily_inputs di
      WHERE di.deleted_at IS NULL
        AND di.entry_date BETWEEN c.prod_date_from AND c.prod_date_to
    )                                   AS inbound_feedstock_kg,

    -- Plant production during window (all consignments share this view)
    (SELECT COUNT(*)
       FROM daily_production dp
      WHERE dp.deleted_at IS NULL
        AND dp.prod_date BETWEEN c.prod_date_from AND c.prod_date_to
        AND dp.output_eu_kg IS NOT NULL AND dp.output_eu_kg > 0
    )                                   AS production_days,

    (SELECT COALESCE(SUM(dp.output_eu_kg), 0)
       FROM daily_production dp
      WHERE dp.deleted_at IS NULL
        AND dp.prod_date BETWEEN c.prod_date_from AND c.prod_date_to
    )                                   AS plant_production_kg,

    -- Inland (Girardot → Cartagena)
    (SELECT COUNT(*)
       FROM inland_shipment i
      WHERE i.consignment_id = c.id AND i.deleted_at IS NULL
    )                                   AS inland_container_count,

    (SELECT COUNT(*)
       FROM inland_shipment i
      WHERE i.consignment_id = c.id AND i.deleted_at IS NULL
        AND i.ersv_inland_no IS NOT NULL
    )                                   AS inland_ersv_alloc_count,

    (SELECT MIN(i.ersv_inland_no)
       FROM inland_shipment i
      WHERE i.consignment_id = c.id AND i.deleted_at IS NULL
        AND i.ersv_inland_no IS NOT NULL
    )                                   AS inland_ersv_first,

    (SELECT MAX(i.ersv_inland_no)
       FROM inland_shipment i
      WHERE i.consignment_id = c.id AND i.deleted_at IS NULL
        AND i.ersv_inland_no IS NOT NULL
    )                                   AS inland_ersv_last,

    (SELECT COALESCE(SUM(i.net_kg), 0)
       FROM inland_shipment i
      WHERE i.consignment_id = c.id AND i.deleted_at IS NULL
    )                                   AS inland_kg_total,

    -- Ocean BL
    (SELECT COUNT(DISTINCT sl.document_ref)
       FROM shipment_leg sl
      WHERE sl.consignment_id = c.id AND sl.deleted_at IS NULL
        AND sl.leg_type = 'bl_ocean'
    )                                   AS bl_ocean_count,

    (SELECT string_agg(DISTINCT sl.document_ref, ', ' ORDER BY sl.document_ref)
       FROM shipment_leg sl
      WHERE sl.consignment_id = c.id AND sl.deleted_at IS NULL
        AND sl.leg_type = 'bl_ocean'
    )                                   AS bl_ocean_refs,

    -- UTB transload residual
    (SELECT sl.kg_stock_residual
       FROM shipment_leg sl
      WHERE sl.consignment_id = c.id AND sl.deleted_at IS NULL
        AND sl.leg_type = 'utb_transload'
      LIMIT 1
    )                                   AS utb_stock_residual_kg,

    -- Downstream PoS / outbound eRSV
    (SELECT COUNT(*)
       FROM consignment_pos cp
      WHERE cp.consignment_id = c.id AND cp.deleted_at IS NULL
    )                                   AS pos_count,

    (SELECT COALESCE(SUM(cp.kg_net), 0)
       FROM consignment_pos cp
      WHERE cp.consignment_id = c.id AND cp.deleted_at IS NULL
    )                                   AS pos_kg_total,

    (SELECT COUNT(*)
       FROM consignment_pos cp
      WHERE cp.consignment_id = c.id AND cp.deleted_at IS NULL
        AND cp.ersv_outbound_no IS NOT NULL
    )                                   AS pos_with_outbound_ersv,

    (SELECT MIN(cp.pos_number)
       FROM consignment_pos cp
      WHERE cp.consignment_id = c.id AND cp.deleted_at IS NULL
    )                                   AS pos_first,

    (SELECT MAX(cp.pos_number)
       FROM consignment_pos cp
      WHERE cp.consignment_id = c.id AND cp.deleted_at IS NULL
    )                                   AS pos_last,

    -- Allocation link table — completeness flag
    (SELECT COUNT(*)
       FROM consignment_production_link cpl
      WHERE cpl.consignment_id = c.id
    )                                   AS production_link_days,

    (SELECT COALESCE(SUM(cpl.kg_allocated), 0)
       FROM consignment_production_link cpl
      WHERE cpl.consignment_id = c.id
    )                                   AS production_link_kg
FROM consignment c
WHERE c.deleted_at IS NULL;
"""


def upgrade() -> None:
    op.execute(_CREATE_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_chain_summary")
