from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DailyEntryBase(BaseModel):
    entry_date: date
    entry_time: time | None = None

    supplier_id: int | None = None
    contract_id: int | None = None
    certificate_id: int | None = None
    ersv_number: str | None = None

    car_kg: Decimal | None = None
    truck_kg: Decimal | None = None
    special_kg: Decimal | None = None

    theor_veg_pct: Decimal | None = None
    manuf_veg_pct: Decimal | None = None

    kg_to_production: Decimal | None = None
    eu_prod_kg: Decimal | None = None
    plus_prod_kg: Decimal | None = None

    c14_analysis: bool | None = None
    c14_value: Decimal | None = None

    carbon_black_kg: Decimal | None = None
    metal_scrap_kg: Decimal | None = None

    h2o_pct: Decimal | None = None
    gas_syngas_pct: Decimal | None = None
    losses_kg: Decimal | None = None

    output_eu_kg: Decimal | None = None
    contract_ref: str | None = None
    pos_number: str | None = None

    hours: Decimal | None = None
    description: str | None = None

    source_file: str | None = None
    source_row: int | None = None


class DailyEntryCreate(DailyEntryBase):
    pass


class DailyEntryUpdate(BaseModel):
    entry_date: date | None = None
    entry_time: time | None = None
    supplier_id: int | None = None
    contract_id: int | None = None
    certificate_id: int | None = None
    ersv_number: str | None = None
    car_kg: Decimal | None = None
    truck_kg: Decimal | None = None
    special_kg: Decimal | None = None
    theor_veg_pct: Decimal | None = None
    manuf_veg_pct: Decimal | None = None
    kg_to_production: Decimal | None = None
    eu_prod_kg: Decimal | None = None
    plus_prod_kg: Decimal | None = None
    c14_analysis: bool | None = None
    c14_value: Decimal | None = None
    carbon_black_kg: Decimal | None = None
    metal_scrap_kg: Decimal | None = None
    h2o_pct: Decimal | None = None
    gas_syngas_pct: Decimal | None = None
    losses_kg: Decimal | None = None
    output_eu_kg: Decimal | None = None
    contract_ref: str | None = None
    pos_number: str | None = None
    hours: Decimal | None = None
    description: str | None = None


class DailyEntryRead(DailyEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # computed column — read-only
    total_input_kg: Decimal | None = None
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime
    deleted_at: datetime | None = None
