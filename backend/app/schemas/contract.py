from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ContractBase(BaseModel):
    code: str
    supplier_id: int
    start_date: date
    end_date: date | None = None
    total_kg_committed: Decimal | None = None
    notes: str | None = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    code: str | None = None
    supplier_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    total_kg_committed: Decimal | None = None
    notes: str | None = None


class ContractRead(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
