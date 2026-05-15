from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RectificationSource = Literal[
    "supplier_letter",
    "internal_audit",
    "dft_request",
    "other",
]


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


class DailyInputRectify(BaseModel):
    """Admin-only write payload to apply a rectification.

    RBAC: gated to role=admin at the router layer (downstream story —
    DFTEN-101 only ships the schema/model surface). The router that
    consumes this must:

      1. require_admin() on the caller's JWT,
      2. snapshot the current row into original_values (JSONB) BEFORE
         applying any change,
      3. set rectified_at = NOW() and rectified_by = current_user.id,
      4. never hard-delete; this is soft-rectification only.
    """

    model_config = ConfigDict(extra="forbid")

    rectification_reason: str = Field(min_length=1)
    rectification_source: RectificationSource
    # Optional field overrides applied as part of the rectification.
    # Whichever fields the admin supplies are written through; the rest
    # of the row is preserved verbatim.
    car_kg: Decimal | None = Field(default=None, ge=0)
    truck_kg: Decimal | None = Field(default=None, ge=0)
    special_kg: Decimal | None = Field(default=None, ge=0)
    ersv_number: str | None = None
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

    # --- Rectification audit (read-only on the response model) -------
    # Populated only after an admin rectification (migration 0006).
    rectified_at: datetime | None = None
    rectified_by: int | None = None
    rectification_reason: str | None = None
    rectification_source: RectificationSource | None = None
    original_values: dict[str, Any] | None = None
