"""Pydantic v2 schemas for logistics downstream entities.

Covers: OffTaker, Consignment, ConsignmentPos, ConsignmentProductionLink,
ShipmentLeg, ShipmentUnit, and the composite ConsignmentDetail for UI.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums — mirror CHECK constraints in models exactly
# ---------------------------------------------------------------------------


class ProductGrade(StrEnum):
    dev_p100 = "DEV-P100"
    dev_p200 = "DEV-P200"


class ConsignmentStatus(StrEnum):
    draft = "draft"
    loaded = "loaded"
    in_transit = "in_transit"
    at_utb = "at_utb"
    delivered_uk = "delivered_uk"
    closed = "closed"


class LegType(StrEnum):
    plant_to_port = "plant_to_port"
    port_loading = "port_loading"
    bl_ocean = "bl_ocean"
    utb_transload = "utb_transload"
    nl_to_uk_export = "nl_to_uk_export"
    delivery_uk = "delivery_uk"


class DocumentType(StrEnum):
    ersv_outbound = "eRSV_outbound"
    port_rsv = "Port_RSV"
    bl_ocean = "BL_ocean"
    transload_report = "transload_report"
    mrn = "MRN"
    bl_road = "BL_road"
    commercial_invoice = "commercial_invoice"


# ---------------------------------------------------------------------------
# OffTaker
# ---------------------------------------------------------------------------


class OffTakerCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1)
    country: str | None = None
    address: str | None = None
    iscc_certificate_id: int | None = None
    notes: str | None = None


class OffTakerUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = None
    country: str | None = None
    address: str | None = None
    iscc_certificate_id: int | None = None
    notes: str | None = None


class OffTakerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    country: str | None
    address: str | None
    iscc_certificate_id: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# ---------------------------------------------------------------------------
# ConsignmentPos
# ---------------------------------------------------------------------------


class ConsignmentPosCreate(BaseModel):
    pos_number: str = Field(..., min_length=1)
    pdf_ref: str | None = None
    kg_net: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    ghg_ep: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=2)] = None
    ghg_etd: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=2)] = None
    ghg_total: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=2)] = None
    ghg_saving_pct: Annotated[
        Decimal | None, Field(default=None, ge=0, le=100, decimal_places=2)
    ] = None


class ConsignmentPosOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    consignment_id: int
    pos_number: str
    pdf_ref: str | None
    kg_net: Decimal | None
    ersv_outbound_no: str | None = None
    ghg_ep: Decimal | None = None
    ghg_etd: Decimal | None = None
    ghg_total: Decimal | None = None
    ghg_saving_pct: Decimal | None = None
    created_at: datetime
    deleted_at: datetime | None = None


# ---------------------------------------------------------------------------
# ConsignmentProductionLink
# ---------------------------------------------------------------------------


class ConsignmentProductionLinkCreate(BaseModel):
    prod_date: date
    kg_allocated: Annotated[Decimal, Field(gt=0, decimal_places=3)]


class ConsignmentProductionLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    consignment_id: int
    prod_date: date
    kg_allocated: Decimal
    created_at: datetime


# ---------------------------------------------------------------------------
# ShipmentUnit
# ---------------------------------------------------------------------------


class ShipmentUnitCreate(BaseModel):
    container_ref: str = Field(..., min_length=1)
    flexitank_ref: str | None = None
    kg_gross: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    kg_tare: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    kg_net: Annotated[Decimal, Field(gt=0, decimal_places=3)]
    notes: str | None = None


class ShipmentUnitUpdate(BaseModel):
    container_ref: str | None = Field(default=None, min_length=1)
    flexitank_ref: str | None = None
    kg_gross: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    kg_tare: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    kg_net: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    notes: str | None = None


class ShipmentUnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    leg_id: int
    container_ref: str
    flexitank_ref: str | None
    kg_gross: Decimal | None
    kg_tare: Decimal | None
    kg_net: Decimal
    notes: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# ShipmentLeg
# ---------------------------------------------------------------------------


class ShipmentLegCreate(BaseModel):
    consignment_id: int
    seq: int = Field(..., ge=1)
    leg_type: LegType
    document_type: DocumentType
    document_ref: str | None = None
    document_date: date | None = None
    carrier: str | None = None
    origin_node: str = Field(..., min_length=1)
    destination_node: str = Field(..., min_length=1)
    kg_in: Annotated[Decimal, Field(gt=0, decimal_places=3)]
    kg_out: Annotated[Decimal, Field(gt=0, decimal_places=3)]
    kg_stock_residual: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=3)] = None
    operator_certificate_id: int | None = None
    notes: str | None = None


class ShipmentLegUpdate(BaseModel):
    seq: int | None = Field(default=None, ge=1)
    leg_type: LegType | None = None
    document_type: DocumentType | None = None
    document_ref: str | None = None
    document_date: date | None = None
    carrier: str | None = None
    origin_node: str | None = Field(default=None, min_length=1)
    destination_node: str | None = Field(default=None, min_length=1)
    kg_in: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    kg_out: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    kg_stock_residual: Annotated[Decimal | None, Field(default=None, ge=0, decimal_places=3)] = None
    operator_certificate_id: int | None = None
    notes: str | None = None


class ShipmentLegOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consignment_id: int
    seq: int
    leg_type: str
    document_type: str
    document_ref: str | None
    document_date: date | None
    carrier: str | None
    origin_node: str
    destination_node: str
    kg_in: Decimal
    kg_out: Decimal
    kg_stock_residual: Decimal | None
    operator_certificate_id: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ShipmentLegDetail(ShipmentLegOut):
    """ShipmentLeg with its units — used in ConsignmentDetail."""

    units: list[ShipmentUnitOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Consignment
# ---------------------------------------------------------------------------


class ConsignmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=128)
    off_taker_id: int
    contract_ref: str | None = None
    product_grade: ProductGrade
    prod_date_from: date | None = None
    prod_date_to: date | None = None
    total_kg: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    ersv_outbound_no: str | None = None
    port_rsv_no: str | None = None
    status: ConsignmentStatus = ConsignmentStatus.draft
    notes: str | None = None


class ConsignmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=128)
    off_taker_id: int | None = None
    contract_ref: str | None = None
    product_grade: ProductGrade | None = None
    prod_date_from: date | None = None
    prod_date_to: date | None = None
    total_kg: Annotated[Decimal | None, Field(default=None, gt=0, decimal_places=3)] = None
    ersv_outbound_no: str | None = None
    port_rsv_no: str | None = None
    status: ConsignmentStatus | None = None
    notes: str | None = None


class ConsignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    off_taker_id: int
    contract_ref: str | None
    product_grade: str
    prod_date_from: date | None
    prod_date_to: date | None
    total_kg: Decimal | None
    ersv_outbound_no: str | None
    port_rsv_no: str | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ConsignmentSummary(ConsignmentOut):
    """List shape: ConsignmentOut + nested off_taker + chain-derived KPI fields.

    KPI fields are computed from leg rows at query time:
      * kg_residual_utb — sum of `kg_stock_residual` across leg_type='utb_transload'
      * kg_delivered_uk — sum of `kg_out` across leg_type='delivery_uk'

    Used by #3 logistics-ui list/index — KPI tiles (UTB stock, Delivered UK) +
    table's off-taker column.
    """

    off_taker: OffTakerOut | None = None
    kg_residual_utb: Decimal | None = None
    kg_delivered_uk: Decimal | None = None


class ConsignmentDetail(ConsignmentOut):
    """Composite view: consignment + nested off_taker + legs (with units) + pos + production links.

    This is the response shape for GET /consignments/{id}.
    Used by #3 logistics-ui for the chain-of-custody detail page.
    """

    off_taker: OffTakerOut | None = None
    legs: list[ShipmentLegDetail] = Field(default_factory=list)
    pos: list[ConsignmentPosOut] = Field(default_factory=list)
    production_links: list[ConsignmentProductionLinkOut] = Field(default_factory=list)
