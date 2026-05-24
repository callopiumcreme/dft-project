"""Inland CO shipments — Girardot plant → Cartagena port (eRSV inland)

Revision ID: 0023_inland_shipment
Revises: 0022_pos_outbound_ersv
Create Date: 2026-05-24

Cliente direction (2026-05-24): the first leg of every outbound consignment is
an intra-OisteBio inland transport from the Girardot pyrolysis plant to the
Cartagena Contecar port terminal. This leg pre-dates every ocean BL and is
materialised one row per 20' ISO container (29 rows for Q3 2025).

The legacy ``shipment_leg`` table aggregates that first leg into a single
``bl_ocean`` row keyed on the BL document. ``inland_shipment`` records the
per-container truth used to render eRSV inland documents (one per container,
ES, signed digitally per Ley 527/1999).

Schema:
  - id                BIGSERIAL PK
  - consignment_id    BIGINT FK consignment(id), NOT NULL
  - bl_ref            TEXT NOT NULL  -- onward BL document_ref
  - seq_in_bl         SMALLINT NOT NULL  -- 1..15 (BL1) or 1..14 (BL2)
  - container_id      VARCHAR(11) NOT NULL  -- ISO 6346, e.g. PCVU3502178
  - seal_ref          TEXT  -- precinto (was "flexitank" in xlsx source)
  - load_date         DATE NOT NULL  -- giorno carico plant Girardot
  - gross_kg          NUMERIC(12,3) NOT NULL
  - tare_kg           NUMERIC(12,3) NOT NULL
  - net_kg            NUMERIC(12,3) NOT NULL
  - ersv_inland_no    TEXT  -- pattern GIR/{yy}/{DD-MM}/{seq:02d}, lazy alloc
  - transporter       TEXT  -- empresa camion, placeholder
  - driver_name       TEXT  -- placeholder
  - vehicle_plate     TEXT  -- placeholder
  - origin_node       TEXT NOT NULL DEFAULT 'Girardot plant (CO)'
  - destination_node  TEXT NOT NULL DEFAULT 'Cartagena Contecar (CO)'
  - notes             TEXT
  - created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
  - updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
  - deleted_at        TIMESTAMPTZ  -- soft-delete

Indexes:
  - UNIQUE active (consignment_id, container_id, load_date) — natural key
  - UNIQUE active ersv_inland_no — partial, NOT NULL only
  - INDEX (consignment_id, load_date, seq_in_bl) — list queries
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0023_inland_shipment"
down_revision = "0022_pos_outbound_ersv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inland_shipment",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "consignment_id",
            sa.BigInteger(),
            sa.ForeignKey("consignment.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("bl_ref", sa.Text(), nullable=False),
        sa.Column("seq_in_bl", sa.SmallInteger(), nullable=False),
        sa.Column("container_id", sa.String(11), nullable=False),
        sa.Column("seal_ref", sa.Text(), nullable=True),
        sa.Column("load_date", sa.Date(), nullable=False),
        sa.Column("gross_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("tare_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("net_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("ersv_inland_no", sa.Text(), nullable=True),
        sa.Column("transporter", sa.Text(), nullable=True),
        sa.Column("driver_name", sa.Text(), nullable=True),
        sa.Column("vehicle_plate", sa.Text(), nullable=True),
        sa.Column(
            "origin_node",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'Girardot plant (CO)'"),
        ),
        sa.Column(
            "destination_node",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'Cartagena Contecar (CO)'"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Natural key — active rows only
    op.create_index(
        "uq_inland_shipment_natural_active",
        "inland_shipment",
        ["consignment_id", "container_id", "load_date"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # eRSV number uniqueness — active + allocated only
    op.create_index(
        "uq_inland_shipment_ersv_no_active",
        "inland_shipment",
        ["ersv_inland_no"],
        unique=True,
        postgresql_where=sa.text(
            "ersv_inland_no IS NOT NULL AND deleted_at IS NULL"
        ),
    )

    # List queries by consignment ordered by date + BL seq
    op.create_index(
        "ix_inland_shipment_consignment_load",
        "inland_shipment",
        ["consignment_id", "load_date", "seq_in_bl"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inland_shipment_consignment_load", table_name="inland_shipment"
    )
    op.drop_index(
        "uq_inland_shipment_ersv_no_active", table_name="inland_shipment"
    )
    op.drop_index(
        "uq_inland_shipment_natural_active", table_name="inland_shipment"
    )
    op.drop_table("inland_shipment")
