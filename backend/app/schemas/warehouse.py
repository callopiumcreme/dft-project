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
    """

    product_kind: ProductKind
    stock_kg: Decimal
    produced_total_kg: Decimal
    dispatched_total_kg: Decimal
    reserved_kg: Decimal
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
