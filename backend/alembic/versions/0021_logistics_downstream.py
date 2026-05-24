"""Logistics downstream — off_taker, consignment, shipment entities

Revision ID: 0021_logistics_downstream
Revises: 0020
Create Date: 2026-05-23

Introduces the full logistics downstream schema for tracking
product shipments from Girardot plant to Crown Oil UK:

  off_taker               — buyer entities (Crown Oil, future buyers)
  consignment             — commercial lot of finished product
  consignment_production_link — M:N bridge: consignment ↔ daily_production days
  consignment_pos         — 1 consignment → N Proof-of-Sustainability docs
  shipment_leg            — individual custody-chain leg (plant→port, BL, transload, ...)
  shipment_unit           — container/tank granularity within a leg

Design decisions (locked 2026-05-23):
  Q1 — M:N bridge table (consignment_production_link) keeps daily_production intact
  Q4 — kg_stock_residual on utb_transload leg (no separate utb_stock entity)
  Q5 — 1 leg per BL + shipment_unit for container granularity
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021_logistics_downstream"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # off_taker
    # ------------------------------------------------------------------
    op.create_table(
        "off_taker",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "iscc_certificate_id",
            sa.BigInteger(),
            sa.ForeignKey("certificates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="uq_off_taker_code"),
    )

    # ------------------------------------------------------------------
    # consignment
    # ------------------------------------------------------------------
    op.create_table(
        "consignment",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column(
            "off_taker_id",
            sa.BigInteger(),
            sa.ForeignKey("off_taker.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("contract_ref", sa.Text(), nullable=True),
        sa.Column("product_grade", sa.Text(), nullable=False),
        sa.Column("prod_date_from", sa.Date(), nullable=True),
        sa.Column("prod_date_to", sa.Date(), nullable=True),
        sa.Column("total_kg", sa.Numeric(14, 3), nullable=True),
        sa.Column("ersv_outbound_no", sa.Text(), nullable=True),
        sa.Column("port_rsv_no", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="uq_consignment_code"),
        sa.CheckConstraint(
            "product_grade IN ('DEV-P100','DEV-P200')",
            name="consignment_product_grade_check",
        ),
        sa.CheckConstraint(
            "status IN ('draft','loaded','in_transit','at_utb','delivered_uk','closed')",
            name="consignment_status_check",
        ),
    )
    op.create_index(
        "ix_consignment_off_taker",
        "consignment",
        ["off_taker_id"],
    )
    op.create_index(
        "ix_consignment_status",
        "consignment",
        ["status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ------------------------------------------------------------------
    # consignment_production_link  (M:N bridge)
    # ------------------------------------------------------------------
    op.create_table(
        "consignment_production_link",
        sa.Column(
            "consignment_id",
            sa.BigInteger(),
            sa.ForeignKey("consignment.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("prod_date", sa.Date(), primary_key=True, nullable=False),
        sa.Column("kg_allocated", sa.Numeric(14, 3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kg_allocated > 0",
            name="consignment_production_link_kg_allocated_positive",
        ),
    )

    # ------------------------------------------------------------------
    # consignment_pos  (1 consignment → N PoS documents)
    # ------------------------------------------------------------------
    op.create_table(
        "consignment_pos",
        sa.Column(
            "consignment_id",
            sa.BigInteger(),
            sa.ForeignKey("consignment.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("pos_number", sa.Text(), primary_key=True, nullable=False),
        sa.Column("pdf_ref", sa.Text(), nullable=True),
        sa.Column("kg_net", sa.Numeric(14, 3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_consignment_pos_pos_number",
        "consignment_pos",
        ["pos_number"],
    )

    # ------------------------------------------------------------------
    # shipment_leg
    # ------------------------------------------------------------------
    op.create_table(
        "shipment_leg",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "consignment_id",
            sa.BigInteger(),
            sa.ForeignKey("consignment.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("leg_type", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("document_ref", sa.Text(), nullable=True),
        sa.Column("document_date", sa.Date(), nullable=True),
        sa.Column("carrier", sa.Text(), nullable=True),
        sa.Column("origin_node", sa.Text(), nullable=False),
        sa.Column("destination_node", sa.Text(), nullable=False),
        sa.Column("kg_in", sa.Numeric(14, 3), nullable=False),
        sa.Column("kg_out", sa.Numeric(14, 3), nullable=False),
        sa.Column("kg_stock_residual", sa.Numeric(14, 3), nullable=True),
        sa.Column(
            "operator_certificate_id",
            sa.BigInteger(),
            sa.ForeignKey("certificates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("consignment_id", "seq", name="uq_shipment_leg_consignment_seq"),
        sa.CheckConstraint(
            "leg_type IN ('plant_to_port','port_loading','bl_ocean',"
            "'utb_transload','nl_to_uk_export','delivery_uk')",
            name="shipment_leg_leg_type_check",
        ),
        sa.CheckConstraint(
            "document_type IN ('eRSV_outbound','Port_RSV','BL_ocean',"
            "'transload_report','MRN','BL_road','commercial_invoice')",
            name="shipment_leg_document_type_check",
        ),
        sa.CheckConstraint(
            "kg_in >= kg_out",
            name="shipment_leg_no_mass_creation",
        ),
        sa.CheckConstraint(
            "leg_type <> 'utb_transload' OR "
            "(kg_stock_residual IS NOT NULL AND kg_in = kg_out + kg_stock_residual)",
            name="shipment_leg_utb_mass_conservation",
        ),
    )
    op.create_index(
        "ix_shipment_leg_consignment_seq",
        "shipment_leg",
        ["consignment_id", "seq"],
    )

    # ------------------------------------------------------------------
    # shipment_unit  (container / tank granularity)
    # ------------------------------------------------------------------
    op.create_table(
        "shipment_unit",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "leg_id",
            sa.BigInteger(),
            sa.ForeignKey("shipment_leg.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("container_ref", sa.Text(), nullable=False),
        sa.Column("flexitank_ref", sa.Text(), nullable=True),
        sa.Column("kg_gross", sa.Numeric(14, 3), nullable=True),
        sa.Column("kg_tare", sa.Numeric(14, 3), nullable=True),
        sa.Column("kg_net", sa.Numeric(14, 3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kg_net > 0",
            name="shipment_unit_kg_net_positive",
        ),
    )
    op.create_index(
        "ix_shipment_unit_leg",
        "shipment_unit",
        ["leg_id"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order:
    # units → legs → pos → prod_link → consignment → off_taker
    op.drop_index("ix_shipment_unit_leg", table_name="shipment_unit")
    op.drop_table("shipment_unit")

    op.drop_index("ix_shipment_leg_consignment_seq", table_name="shipment_leg")
    op.drop_table("shipment_leg")

    op.drop_index("ix_consignment_pos_pos_number", table_name="consignment_pos")
    op.drop_table("consignment_pos")

    op.drop_table("consignment_production_link")

    op.drop_index("ix_consignment_status", table_name="consignment")
    op.drop_index("ix_consignment_off_taker", table_name="consignment")
    op.drop_table("consignment")

    op.drop_table("off_taker")
