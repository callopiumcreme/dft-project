from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.daily_entry import DailyEntry
from app.routers.auth import CurrentUser
from app.schemas.daily_entry import DailyEntryCreate, DailyEntryRead, DailyEntryUpdate

router = APIRouter(prefix="/daily-entries", tags=["daily-entries"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _entry_snapshot(obj: DailyEntry) -> dict[str, Any]:
    return {
        c.key: (str(getattr(obj, c.key)) if getattr(obj, c.key) is not None else None)
        for c in obj.__mapper__.column_attrs
    }


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None


async def _write_audit(
    db: AsyncSession,
    action: str,
    record_id: int,
    user_id: int | None,
    ip: str | None,
    old: dict[str, Any] | None = None,
    new: dict[str, Any] | None = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        table_name="daily_entries",
        record_id=record_id,
        old_values=old,
        new_values=new,
        ip_address=ip,
    )
    db.add(log)


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
async def create_daily_entry(
    request: Request,
    body: DailyEntryCreate,
    db: DbDep,
    current_user: CurrentUser,
) -> DailyEntry:
    obj = DailyEntry(**body.model_dump(), created_by=current_user.id)
    db.add(obj)
    await db.flush()
    snapshot = _entry_snapshot(obj)
    await _write_audit(db, "INSERT", obj.id, current_user.id, _client_ip(request), new=snapshot)
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
async def update_daily_entry(
    request: Request,
    entry_id: int,
    body: DailyEntryUpdate,
    db: DbDep,
    current_user: CurrentUser,
) -> DailyEntry:
    obj = await db.get(DailyEntry, entry_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Daily entry not found")
    old_snapshot = _entry_snapshot(obj)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.updated_by = current_user.id
    obj.updated_at = datetime.utcnow()
    new_snapshot = _entry_snapshot(obj)
    await _write_audit(db, "UPDATE", obj.id, current_user.id, _client_ip(request), old=old_snapshot, new=new_snapshot)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{entry_id}", status_code=204)
async def delete_daily_entry(
    request: Request,
    entry_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> None:
    obj = await db.get(DailyEntry, entry_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Daily entry not found")
    old_snapshot = _entry_snapshot(obj)
    obj.deleted_at = datetime.utcnow()
    obj.updated_by = current_user.id
    await _write_audit(db, "DELETE", obj.id, current_user.id, _client_ip(request), old=old_snapshot)
    await db.commit()
