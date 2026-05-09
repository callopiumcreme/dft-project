"""Read-only mass-balance + analytics reports.

Backed by mv_mass_balance_daily / mv_mass_balance_monthly + live
aggregates over daily_inputs joined to suppliers. All endpoints viewer+.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ViewerUser
from app.db.session import get_db
from app.schemas.reports import (
    BySupplierRow,
    ClosureStatusRow,
    MassBalanceDailyRow,
    MassBalanceMonthlyRow,
)

router = APIRouter(prefix="/reports", tags=["reports"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/mass-balance/daily", response_model=list[MassBalanceDailyRow])
async def mass_balance_daily(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(366, ge=1, le=3660),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    where = []
    params: dict = {"limit": limit, "offset": offset}
    if date_from is not None:
        where.append("day >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        where.append("day <= :date_to")
        params["date_to"] = date_to
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"""
        SELECT day, input_total_kg, kg_to_production, eu_prod_kg, plus_prod_kg,
               carbon_black_kg, metal_scrap_kg, h2o_kg, gas_syngas_kg,
               losses_kg, output_eu_kg, output_total_kg, closure_diff_pct
        FROM mv_mass_balance_daily
        {where_sql}
        ORDER BY day DESC
        LIMIT :limit OFFSET :offset
        """
    )
    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


@router.get("/mass-balance/monthly", response_model=list[MassBalanceMonthlyRow])
async def mass_balance_monthly(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None, description="month start (e.g., 2025-01-01)"),
    date_to: date | None = Query(None),
) -> list[dict]:
    where = []
    params: dict = {}
    if date_from is not None:
        where.append("month >= CAST(date_trunc('month', CAST(:date_from AS date)) AS date)")
        params["date_from"] = date_from
    if date_to is not None:
        where.append("month <= CAST(date_trunc('month', CAST(:date_to AS date)) AS date)")
        params["date_to"] = date_to
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"""
        SELECT month, input_total_kg, eu_prod_kg, plus_prod_kg, carbon_black_kg,
               metal_scrap_kg, h2o_kg, gas_syngas_kg, losses_kg, output_eu_kg,
               output_total_kg, closure_diff_pct
        FROM mv_mass_balance_monthly
        {where_sql}
        ORDER BY month DESC
        """
    )
    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


@router.get("/by-supplier", response_model=list[BySupplierRow])
async def by_supplier(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[dict]:
    where = ["di.deleted_at IS NULL", "s.deleted_at IS NULL"]
    params: dict = {}
    if date_from is not None:
        where.append("di.entry_date >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        where.append("di.entry_date <= :date_to")
        params["date_to"] = date_to
    where_sql = "WHERE " + " AND ".join(where)
    sql = text(
        f"""
        SELECT s.id  AS supplier_id,
               s.code AS supplier_code,
               s.name AS supplier_name,
               SUM(di.total_input_kg) AS total_input_kg,
               COUNT(*)               AS entries,
               COUNT(DISTINCT di.entry_date) AS days
        FROM daily_inputs di
        JOIN suppliers s ON s.id = di.supplier_id
        {where_sql}
        GROUP BY s.id, s.code, s.name
        ORDER BY total_input_kg DESC
        """
    )
    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


@router.get("/closure-status", response_model=list[ClosureStatusRow])
async def closure_status(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[dict]:
    where = []
    params: dict = {}
    if date_from is not None:
        where.append("day >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        where.append("day <= :date_to")
        params["date_to"] = date_to
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"""
        SELECT day, input_total_kg, output_total_kg, closure_diff_pct,
               CASE
                 WHEN COALESCE(input_total_kg, 0) = 0 THEN 'no_input'
                 WHEN COALESCE(output_total_kg, 0) = 0 THEN 'no_output'
                 WHEN ABS(closure_diff_pct) <= 2 THEN 'ok'
                 WHEN ABS(closure_diff_pct) <= 5 THEN 'warn'
                 ELSE 'alert'
               END AS bucket
        FROM mv_mass_balance_daily
        {where_sql}
        ORDER BY day DESC
        """
    )
    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]
