"""Read-only response schemas for /reports/*."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class MassBalanceDailyRow(BaseModel):
    day: date
    input_total_kg: Decimal | None = None
    kg_to_production: Decimal | None = None
    eu_prod_kg: Decimal | None = None
    plus_prod_kg: Decimal | None = None
    carbon_black_kg: Decimal | None = None
    metal_scrap_kg: Decimal | None = None
    h2o_kg: Decimal | None = None
    gas_syngas_kg: Decimal | None = None
    losses_kg: Decimal | None = None
    output_eu_kg: Decimal | None = None
    eu_prod_litres: Decimal | None = None
    plus_prod_litres: Decimal | None = None
    total_prod_litres: Decimal | None = None
    output_total_kg: Decimal | None = None
    closure_diff_pct: Decimal | None = None


class MassBalanceMonthlyRow(BaseModel):
    month: date
    input_total_kg: Decimal | None = None
    eu_prod_kg: Decimal | None = None
    plus_prod_kg: Decimal | None = None
    carbon_black_kg: Decimal | None = None
    metal_scrap_kg: Decimal | None = None
    h2o_kg: Decimal | None = None
    gas_syngas_kg: Decimal | None = None
    losses_kg: Decimal | None = None
    output_eu_kg: Decimal | None = None
    eu_prod_litres: Decimal | None = None
    plus_prod_litres: Decimal | None = None
    total_prod_litres: Decimal | None = None
    output_total_kg: Decimal | None = None
    closure_diff_pct: Decimal | None = None


class BySupplierRow(BaseModel):
    supplier_id: int
    supplier_code: str
    supplier_name: str
    total_input_kg: Decimal
    entries: int
    days: int


class ClosureStatusRow(BaseModel):
    day: date
    input_total_kg: Decimal | None = None
    output_total_kg: Decimal | None = None
    closure_diff_pct: Decimal | None = None
    bucket: str  # 'ok' (|pct|<=2), 'warn' (<=5), 'alert' (>5), 'no_input', 'no_output'
