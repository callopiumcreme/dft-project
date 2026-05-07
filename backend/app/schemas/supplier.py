from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SupplierBase(BaseModel):
    name: str
    code: str | None = None
    country: str = "CO"
    active: bool = True
    notes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    country: str | None = None
    active: bool | None = None
    notes: str | None = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
