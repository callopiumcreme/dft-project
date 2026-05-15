from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DailyProductionBase(BaseModel):
    prod_date: date
    kg_to_production: Decimal | None = None
    eu_prod_kg: Decimal | None = None
    plus_prod_kg: Decimal | None = None
    carbon_black_kg: Decimal | None = None
    metal_scrap_kg: Decimal | None = None
    h2o_kg: Decimal | None = None
    gas_syngas_kg: Decimal | None = None
    losses_kg: Decimal | None = None
    output_eu_kg: Decimal | None = None
    contract_ref: str | None = None
    pos_number: str | None = None
    notes: str | None = None


class DailyProductionCreate(DailyProductionBase):
    source_file: str | None = None
    source_row: int | None = None


class DailyProductionUpdate(BaseModel):
    kg_to_production: Decimal | None = None
    eu_prod_kg: Decimal | None = None
    plus_prod_kg: Decimal | None = None
    carbon_black_kg: Decimal | None = None
    metal_scrap_kg: Decimal | None = None
    h2o_kg: Decimal | None = None
    gas_syngas_kg: Decimal | None = None
    losses_kg: Decimal | None = None
    output_eu_kg: Decimal | None = None
    contract_ref: str | None = None
    pos_number: str | None = None
    notes: str | None = None


class DailyProductionRead(DailyProductionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # GENERATED ALWAYS in DB (migration 0007) — exposed read-only here.
    litres_eu: Decimal | None = None
    litres_plus: Decimal | None = None
    source_file: str | None = None
    source_row: int | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    created_by: int | None = None
    updated_by: int | None = None
