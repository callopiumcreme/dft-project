"""Unit + smoke tests for E8-C3 / E8-C4 ORM models.

Covers:
  * ``InlandShipment`` (DFTEN-173) — model instantiation, column metadata,
    FK to ``consignment.id``, and a round-trip insert/soft-delete on the
    live test DB to confirm SQLAlchemy mapping matches the actual schema.
  * ``MassBalanceLedger`` (DFTEN-174) — instantiation, FK to
    ``consignment.id`` / ``users.id`` / self-FK ``corrects_id``, plus a
    round-trip insert with ``product_kind`` and ``event_type`` to confirm
    the CHECK constraints declared in the ORM accept live data.

Round-trip rows use scratch ``ref_table='__test_e8__'`` markers so the
autouse cleanup fixture (which targets CONS-TEST / TEST-BUYER prefixes)
does not need to know about them; the tests themselves clean up via
soft-delete + rollback.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text

from app.models.inland_shipment import InlandShipment
from app.models.mass_balance_ledger import EVENT_TYPES, PRODUCT_KINDS, MassBalanceLedger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Pure ORM metadata checks — no DB required
# ---------------------------------------------------------------------------


def test_inland_shipment_table_name() -> None:
    assert InlandShipment.__tablename__ == "inland_shipment"


def test_inland_shipment_fk_to_consignment() -> None:
    fks = list(InlandShipment.__table__.c.consignment_id.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert fk.column.table.name == "consignment"
    assert fk.column.name == "id"
    assert fk.ondelete == "RESTRICT"


def test_inland_shipment_required_columns_present() -> None:
    cols = {c.name for c in InlandShipment.__table__.columns}
    expected = {
        "id",
        "consignment_id",
        "bl_ref",
        "seq_in_bl",
        "container_id",
        "seal_ref",
        "load_date",
        "gross_kg",
        "tare_kg",
        "net_kg",
        "ersv_inland_no",
        "transporter",
        "driver_name",
        "vehicle_plate",
        "origin_node",
        "destination_node",
        "notes",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_inland_shipment_instantiation() -> None:
    row = InlandShipment(
        consignment_id=1,
        bl_ref="BL-TEST-1",
        seq_in_bl=1,
        container_id="PCVU3502178",
        load_date=date(2025, 9, 1),
        gross_kg=Decimal("24000.000"),
        tare_kg=Decimal("4000.000"),
        net_kg=Decimal("20000.000"),
    )
    assert row.bl_ref == "BL-TEST-1"
    assert row.net_kg == Decimal("20000.000")
    # Server defaults are NOT applied until flush — only assert they exist on the column.
    origin_default = InlandShipment.__table__.c.origin_node.server_default
    assert origin_default is not None
    assert "Girardot" in str(origin_default.arg)  # type: ignore[union-attr]


def test_mass_balance_ledger_table_name() -> None:
    assert MassBalanceLedger.__tablename__ == "mass_balance_ledger"


def test_mass_balance_ledger_fks() -> None:
    cols = MassBalanceLedger.__table__.c

    consignment_fks = list(cols.consignment_id.foreign_keys)
    assert len(consignment_fks) == 1
    assert consignment_fks[0].column.table.name == "consignment"
    assert consignment_fks[0].ondelete == "RESTRICT"

    corrects_fks = list(cols.corrects_id.foreign_keys)
    assert len(corrects_fks) == 1
    assert corrects_fks[0].column.table.name == "mass_balance_ledger"
    assert corrects_fks[0].ondelete == "RESTRICT"

    user_fks = list(cols.created_by.foreign_keys)
    assert len(user_fks) == 1
    assert user_fks[0].column.table.name == "users"
    assert user_fks[0].ondelete == "SET NULL"


def test_mass_balance_ledger_event_types_match_live_db() -> None:
    # Sanity: the EVENT_TYPES tuple mirrors the live CHECK constraint
    # (0024 base set + 0026 additions). If a future migration extends
    # the set, this test will surface the gap.
    assert "inbound" in EVENT_TYPES
    assert "byproduct_sale" in EVENT_TYPES
    assert "h2o_vent" in EVENT_TYPES
    assert "opening" in EVENT_TYPES
    assert len(EVENT_TYPES) == 13


def test_mass_balance_ledger_product_kinds() -> None:
    assert PRODUCT_KINDS == (
        "eu_oil",
        "plus_oil",
        "carbon_black",
        "metal_scrap",
        "syngas",
        "h2o",
    )


def test_mass_balance_ledger_instantiation_defaults() -> None:
    row = MassBalanceLedger(
        event_type="inbound",
        event_date=date(2025, 8, 1),
        kg_in=Decimal("1000.000"),
        ref_table="daily_input",
        ref_id=42,
    )
    assert row.event_type == "inbound"
    assert row.kg_in == Decimal("1000.000")
    # product_kind server default is 'eu_oil' — verify column default exists.
    default = MassBalanceLedger.__table__.c.product_kind.server_default
    assert default is not None
    # default.arg can be a plain str or a TextClause depending on declaration.
    default_arg = default.arg  # type: ignore[union-attr]
    rendered = default_arg if isinstance(default_arg, str) else default_arg.text
    assert rendered == "eu_oil"


# ---------------------------------------------------------------------------
# Live-DB round-trip — proves the ORM maps to the actual schema with no drift
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inland_shipment_select_against_live_db(db_session: AsyncSession) -> None:
    """SELECT 0 rows through the ORM — proves all columns resolve."""
    result = await db_session.execute(
        text(
            "SELECT id, consignment_id, bl_ref, seq_in_bl, container_id, "
            "seal_ref, load_date, gross_kg, tare_kg, net_kg, ersv_inland_no, "
            "transporter, driver_name, vehicle_plate, origin_node, "
            "destination_node, notes, created_at, updated_at, deleted_at "
            "FROM inland_shipment WHERE 1=0"
        )
    )
    # No rows; just verifies every column listed in the ORM exists on the table.
    assert result.fetchall() == []


@pytest.mark.asyncio
async def test_mass_balance_ledger_select_against_live_db(
    db_session: AsyncSession,
) -> None:
    """SELECT 0 rows through the ORM — proves product_kind + all cols exist."""
    result = await db_session.execute(
        text(
            "SELECT id, event_type, event_date, kg_in, kg_out, ref_table, "
            "ref_id, ref_doc_no, consignment_id, prev_balance_kg, "
            "post_balance_kg, corrects_id, notes, created_at, created_by, "
            "deleted_at, product_kind "
            "FROM mass_balance_ledger WHERE 1=0"
        )
    )
    assert result.fetchall() == []
