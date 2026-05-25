"""Pydantic v2 schemas for inland_shipment.

Read-only Out shape mirrors the ``InlandShipment`` ORM. Create/Update bodies
included for future routers (eRSV inland authoring flow); not currently wired
to any endpoint — kept narrow on purpose. Mass-conservation rule
(``gross_kg = tare_kg + net_kg``) is enforced at DB level via the
``ersv_renderer`` raw-SQL path and will be re-asserted here when a write
router is built (see DFTEN gap analysis 2026-05-25).
"""
from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 — Pydantic resolves at runtime
from decimal import Decimal  # noqa: TC003 — Pydantic resolves at runtime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class InlandShipmentCreate(BaseModel):
    consignment_id: int
    bl_ref: str = Field(..., min_length=1)
    seq_in_bl: int = Field(..., ge=1)
    container_id: str = Field(..., min_length=4, max_length=11)
    seal_ref: str | None = None
    load_date: date
    gross_kg: Annotated[Decimal, Field(gt=0, decimal_places=3)]
    tare_kg: Annotated[Decimal, Field(gt=0, decimal_places=3)]
    net_kg: Annotated[Decimal, Field(gt=0, decimal_places=3)]
    ersv_inland_no: str | None = None
    transporter: str | None = None
    driver_name: str | None = None
    vehicle_plate: str | None = None
    origin_node: str = Field(default="Girardot plant (CO)", min_length=1)
    destination_node: str = Field(default="Cartagena Contecar (CO)", min_length=1)
    notes: str | None = None


class InlandShipmentUpdate(BaseModel):
    bl_ref: str | None = Field(default=None, min_length=1)
    seq_in_bl: int | None = Field(default=None, ge=1)
    container_id: str | None = Field(default=None, min_length=4, max_length=11)
    seal_ref: str | None = None
    load_date: date | None = None
    gross_kg: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    tare_kg: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    net_kg: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    ersv_inland_no: str | None = None
    transporter: str | None = None
    driver_name: str | None = None
    vehicle_plate: str | None = None
    origin_node: str | None = Field(default=None, min_length=1)
    destination_node: str | None = Field(default=None, min_length=1)
    notes: str | None = None


class InlandShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consignment_id: int
    bl_ref: str
    seq_in_bl: int
    container_id: str
    seal_ref: str | None
    load_date: date
    gross_kg: Decimal
    tare_kg: Decimal
    net_kg: Decimal
    ersv_inland_no: str | None
    transporter: str | None
    driver_name: str | None
    vehicle_plate: str | None
    origin_node: str
    destination_node: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
