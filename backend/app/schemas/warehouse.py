"""Pydantic v2 schemas for warehouse stock + byproduct sales.

Backs the /warehouse and /byproduct routers introduced with migration 0026
(warehouse_inventory). See alembic/versions/0026_warehouse_inventory.py for
the underlying tables and views.
"""
from __future__ import annotations

from datetime import date, datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProductKind = Literal[
    "eu_oil",
    "plus_oil",
    "carbon_black",
    "metal_scrap",
    "syngas",
    "h2o",
]
SellableKind = Literal["plus_oil", "carbon_black", "metal_scrap"]


class WarehouseStockRow(BaseModel):
    """One row per product_kind from v_warehouse_stock + reserved_kg overlay.

    reserved_kg is computed in the router (not in the view): sum of
    consignment.total_kg for active consignments whose status is not
    delivered_uk / closed. Only meaningful for eu_oil — other kinds are 0.

    pos_issued_kg = SUM(consignment_pos.kg_net) for the same set of active
    consignments (POS already issued, awaiting delivery). Only meaningful
    for eu_oil.

    at_utb_awaiting_pos_kg = reserved_kg - pos_issued_kg (residual reserved
    stock at UTB that has no POS yet). Only meaningful for eu_oil.

    produced_ytd_kg = SUM(kg_in) where event_date falls in the most-recent
    operational year (carried forward automatically by the view as data
    accrues). opening_balance_kg = SUM(kg_in) for any prior year (i.e.
    inception / carry-over rows). produced_total_kg stays equal to the sum
    of the two so existing consumers do not break.
    """

    product_kind: ProductKind
    stock_kg: Decimal
    produced_total_kg: Decimal
    dispatched_total_kg: Decimal
    produced_ytd_kg: Decimal
    opening_balance_kg: Decimal
    reserved_kg: Decimal
    pos_issued_kg: Decimal
    pos_issued_by_year: dict[str, Decimal] = Field(default_factory=dict)
    at_utb_awaiting_pos_kg: Decimal
    last_movement_at: date | None

    model_config = ConfigDict(from_attributes=True)


class WarehouseMovement(BaseModel):
    """One row from mass_balance_ledger (active rows only)."""

    id: int
    event_date: date
    event_type: str
    product_kind: ProductKind
    kg_in: Decimal
    kg_out: Decimal
    post_balance_kg: Decimal | None
    ref_doc_no: str | None
    consignment_id: int | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class ByproductBuyerIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    country: str | None = None
    vat: str | None = None
    contact: str | None = None
    notes: str | None = None


class ByproductBuyerOut(ByproductBuyerIn):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ByproductBuyerUpdate(BaseModel):
    """PATCH body for /byproduct/buyers/{id}.

    All fields optional; only those explicitly supplied are written via the
    Pydantic ``model_dump(exclude_unset=True)`` pattern. ``name`` keeps the
    same length bounds as the create-shape so renames go through the same
    UNIQUE-on-active-rows check.
    """

    name: str | None = Field(default=None, min_length=2, max_length=200)
    country: str | None = None
    vat: str | None = None
    contact: str | None = None
    notes: str | None = None


class ByproductSaleIn(BaseModel):
    product_kind: SellableKind
    buyer_id: int
    sale_date: date
    kg_net: Decimal = Field(gt=0)
    invoice_no: str | None = None
    price_eur: Decimal | None = None
    notes: str | None = None


class ByproductSaleOut(ByproductSaleIn):
    id: int
    created_at: datetime
    buyer_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
