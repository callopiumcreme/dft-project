from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductPurchaseBase(BaseModel):
    pos_number: str
    supplier_id: int | None = None
    certificate_id: int | None = None
    contract_id: int | None = None
    issuance_date: date | None = None
    dispatch_label: str | None = None
    quantity_kg: Decimal | None = None
    feedstock: str | None = None
    notes: str | None = None


class ProductPurchaseCreate(ProductPurchaseBase):
    pass


class ProductPurchaseUpdate(BaseModel):
    pos_number: str | None = None
    supplier_id: int | None = None
    certificate_id: int | None = None
    contract_id: int | None = None
    issuance_date: date | None = None
    dispatch_label: str | None = None
    quantity_kg: Decimal | None = None
    feedstock: str | None = None
    notes: str | None = None


class ProductPurchaseRead(ProductPurchaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_name: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
