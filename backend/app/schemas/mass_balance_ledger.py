"""Pydantic v2 schemas for mass_balance_ledger.

Read-only Out shape is the primary use — the ledger is append-only and
written by service-layer code (currently raw SQL in backfill scripts), so
Create here is provided for completeness and to validate event_type /
product_kind enum membership at the application boundary.

Enums mirror the live DB CHECK constraints (see ``MassBalanceLedger``).
"""
from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 — Pydantic resolves at runtime
from decimal import Decimal  # noqa: TC003 — Pydantic resolves at runtime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LedgerEventType(StrEnum):
    inbound = "inbound"
    production = "production"
    consign_assign = "consign_assign"
    inland_dispatch = "inland_dispatch"
    bl_load = "bl_load"
    utb_transload = "utb_transload"
    pos_issue = "pos_issue"
    uk_delivery = "uk_delivery"
    correction = "correction"
    opening = "opening"
    byproduct_sale = "byproduct_sale"
    syngas_burn = "syngas_burn"
    h2o_vent = "h2o_vent"


class LedgerProductKind(StrEnum):
    eu_oil = "eu_oil"
    plus_oil = "plus_oil"
    carbon_black = "carbon_black"
    metal_scrap = "metal_scrap"
    syngas = "syngas"
    h2o = "h2o"


class MassBalanceLedgerCreate(BaseModel):
    """Validates a single ledger row before it hits the DB.

    Mirrors the four CHECK constraints on ``mass_balance_ledger``:
      * event_type ∈ enum
      * product_kind ∈ enum
      * kg_in or kg_out must be non-NULL (at least one)
      * both kg_in/kg_out non-negative when present
    """

    event_type: LedgerEventType
    event_date: date
    kg_in: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=3)] = None
    kg_out: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=3)] = None
    ref_table: str = Field(..., min_length=1)
    ref_id: int
    ref_doc_no: str | None = None
    consignment_id: int | None = None
    prev_balance_kg: Annotated[Decimal | None, Field(default=None, decimal_places=3)] = None
    post_balance_kg: Annotated[Decimal | None, Field(default=None, decimal_places=3)] = None
    corrects_id: int | None = None
    notes: str | None = None
    created_by: int | None = None
    product_kind: LedgerProductKind = LedgerProductKind.eu_oil

    @model_validator(mode="after")
    def _at_least_one_kg(self) -> MassBalanceLedgerCreate:
        if self.kg_in is None and self.kg_out is None:
            raise ValueError("At least one of kg_in / kg_out must be set")
        return self


class MassBalanceLedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    event_date: date
    kg_in: Decimal | None
    kg_out: Decimal | None
    ref_table: str
    ref_id: int
    ref_doc_no: str | None
    consignment_id: int | None
    prev_balance_kg: Decimal | None
    post_balance_kg: Decimal | None
    corrects_id: int | None
    notes: str | None
    created_at: datetime
    created_by: int | None
    deleted_at: datetime | None
    product_kind: str
