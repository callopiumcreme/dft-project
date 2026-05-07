from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.daily_entry import DailyEntry
from app.schemas.daily_entry import DailyEntryCreate, DailyEntryRead, DailyEntryUpdate

router = APIRouter(prefix="/daily-entries", tags=["daily-entries"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=list[DailyEntryRead])
async def list_daily_entries(
    db: DbDep,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    supplier_id: int | None = Query(default=None),
    contract_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[DailyEntry]:
    stmt = select(DailyEntry).where(DailyEntry.deleted_at.is_(None))
    if date_from is not None:
        stmt = stmt.where(DailyEntry.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyEntry.entry_date <= date_to)
    if supplier_id is not None:
        stmt = stmt.where(DailyEntry.supplier_id == supplier_id)
    if contract_id is not None:
        stmt = stmt.where(DailyEntry.contract_id == contract_id)
    stmt = stmt.offset(skip).limit(limit).order_by(DailyEntry.entry_date.desc(), DailyEntry.id.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=DailyEntryRead, status_code=201)
async def create_daily_entry(body: DailyEntryCreate, db: DbDep) -> DailyEntry:
    obj = DailyEntry(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{entry_id}", response_model=DailyEntryRead)
async def get_daily_entry(entry_id: int, db: DbDep) -> DailyEntry:
    obj = await db.get(DailyEntry, entry_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Daily entry not found")
    return obj


@router.patch("/{entry_id}", response_model=DailyEntryRead)
async def update_daily_entry(entry_id: int, body: DailyEntryUpdate, db: DbDep) -> DailyEntry:
    obj = await db.get(DailyEntry, entry_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Daily entry not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{entry_id}", status_code=204)
async def delete_daily_entry(entry_id: int, db: DbDep) -> None:
    obj = await db.get(DailyEntry, entry_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Daily entry not found")
    obj.deleted_at = datetime.now(timezone.utc)
    await db.commit()
