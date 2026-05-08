from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DailyInputBase(BaseModel):
    entry_date: date
    entry_time: time | None = None
    supplier_id: int
    certificate_id: int | None = None
    contract_id: int | None = None
    ersv_number: str | None = None
    car_kg: Decimal = Field(default=Decimal("0"), ge=0)
    truck_kg: Decimal = Field(default=Decimal("0"), ge=0)
    special_kg: Decimal = Field(default=Decimal("0"), ge=0)
    theor_veg_pct: Decimal | None = None
    manuf_veg_pct: Decimal | None = None
    c14_analysis: str | None = None
    c14_value: Decimal | None = None
    notes: str | None = None


class DailyInputCreate(DailyInputBase):
    source_file: str | None = None
    source_row: int | None = None


class DailyInputUpdate(BaseModel):
    entry_date: date | None = None
    entry_time: time | None = None
    supplier_id: int | None = None
    certificate_id: int | None = None
    contract_id: int | None = None
    ersv_number: str | None = None
    car_kg: Decimal | None = None
    truck_kg: Decimal | None = None
    special_kg: Decimal | None = None
    theor_veg_pct: Decimal | None = None
    manuf_veg_pct: Decimal | None = None
    c14_analysis: str | None = None
    c14_value: Decimal | None = None
    notes: str | None = None


class DailyInputRead(DailyInputBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total_input_kg: Decimal
    source_file: str | None = None
    source_row: int | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    created_by: int | None = None
    updated_by: int | None = None
