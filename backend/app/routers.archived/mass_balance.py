from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import text

from app.db.session import engine

router = APIRouter(prefix="/mass-balance", tags=["mass-balance"])


@router.get("/daily")
async def get_daily_balance(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> list[dict]:
    stmt = "SELECT * FROM mv_mass_balance_daily WHERE 1=1"
    params: dict = {}
    if date_from is not None:
        stmt += " AND entry_date >= :date_from"
        params["date_from"] = date_from
    if date_to is not None:
        stmt += " AND entry_date <= :date_to"
        params["date_to"] = date_to
    stmt += " ORDER BY entry_date DESC"
    async with engine.connect() as conn:
        result = await conn.execute(text(stmt), params)
        return [dict(row._mapping) for row in result]


@router.get("/monthly")
async def get_monthly_balance(
    month_from: date | None = Query(default=None),
    month_to: date | None = Query(default=None),
    supplier_id: int | None = Query(default=None),
) -> list[dict]:
    stmt = "SELECT * FROM mv_mass_balance_monthly WHERE 1=1"
    params: dict = {}
    if month_from is not None:
        stmt += " AND month >= :month_from"
        params["month_from"] = month_from
    if month_to is not None:
        stmt += " AND month <= :month_to"
        params["month_to"] = month_to
    if supplier_id is not None:
        stmt += " AND supplier_id = :supplier_id"
        params["supplier_id"] = supplier_id
    stmt += " ORDER BY month DESC, supplier_id"
    async with engine.connect() as conn:
        result = await conn.execute(text(stmt), params)
        return [dict(row._mapping) for row in result]


@router.post("/refresh", status_code=200)
async def refresh_mass_balance() -> dict[str, str]:
    # REFRESH MATERIALIZED VIEW CONCURRENTLY cannot run inside a transaction.
    # execution_options() returns a new object — must be set on engine before connect().
    async with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
        await conn.execute(text("SELECT refresh_mass_balance_views()"))
    return {"status": "refreshed"}
