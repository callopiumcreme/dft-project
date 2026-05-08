"""CRUD /daily-inputs with audit log + soft delete.

- Read: viewer+
- Write: operator+
- Soft delete via deleted_at (no hard delete).
- total_input_kg is GENERATED — never written.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import OperatorUser, ViewerUser
from app.db.session import get_db
from app.models.daily_input import DailyInput
from app.schemas.daily_input import DailyInputCreate, DailyInputRead, DailyInputUpdate
from app.services.audit import model_snapshot, write_audit

router = APIRouter(prefix="/daily-inputs", tags=["daily-inputs"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
TABLE = "daily_inputs"


@router.get("", response_model=list[DailyInputRead])
async def list_daily_inputs(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    supplier_id: int | None = Query(None),
    include_deleted: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[DailyInput]:
    stmt = select(DailyInput)
    if not include_deleted:
        stmt = stmt.where(DailyInput.deleted_at.is_(None))
    if date_from is not None:
        stmt = stmt.where(DailyInput.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyInput.entry_date <= date_to)
    if supplier_id is not None:
        stmt = stmt.where(DailyInput.supplier_id == supplier_id)
    stmt = stmt.order_by(DailyInput.entry_date.desc(), DailyInput.id.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/count")
async def count_daily_inputs(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    supplier_id: int | None = Query(None),
    include_deleted: bool = Query(False),
) -> dict[str, int]:
    stmt = select(func.count(DailyInput.id))
    if not include_deleted:
        stmt = stmt.where(DailyInput.deleted_at.is_(None))
    if date_from is not None:
        stmt = stmt.where(DailyInput.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyInput.entry_date <= date_to)
    if supplier_id is not None:
        stmt = stmt.where(DailyInput.supplier_id == supplier_id)
    result = await db.execute(stmt)
    return {"count": int(result.scalar_one())}


async def _get_or_404(db: AsyncSession, entry_id: int, *, include_deleted: bool = False) -> DailyInput:
    stmt = select(DailyInput).where(DailyInput.id == entry_id)
    if not include_deleted:
        stmt = stmt.where(DailyInput.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DailyInput not found")
    return obj


@router.get("/{entry_id}", response_model=DailyInputRead)
async def get_daily_input(
    entry_id: int,
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
) -> DailyInput:
    return await _get_or_404(db, entry_id, include_deleted=include_deleted)


@router.post("", response_model=DailyInputRead, status_code=status.HTTP_201_CREATED)
async def create_daily_input(
    body: DailyInputCreate,
    user: OperatorUser,
    db: DbDep,
) -> DailyInput:
    obj = DailyInput(**body.model_dump(), created_by=user.id, updated_by=user.id)
    db.add(obj)
    await db.flush()  # populate id + generated total_input_kg
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/{entry_id}", response_model=DailyInputRead)
async def update_daily_input(
    entry_id: int,
    body: DailyInputUpdate,
    user: OperatorUser,
    db: DbDep,
) -> DailyInput:
    obj = await _get_or_404(db, entry_id)
    old = model_snapshot(obj)
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    for k, v in patch.items():
        setattr(obj, k, v)
    obj.updated_by = user.id
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=TABLE,
        record_id=obj.id,
        action="update",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_daily_input(
    entry_id: int,
    user: OperatorUser,
    db: DbDep,
) -> None:
    obj = await _get_or_404(db, entry_id)
    old = model_snapshot(obj)
    obj.deleted_at = datetime.utcnow()
    obj.updated_by = user.id
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=TABLE,
        record_id=obj.id,
        action="soft_delete",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()


@router.post("/{entry_id}/restore", response_model=DailyInputRead)
async def restore_daily_input(
    entry_id: int,
    user: OperatorUser,
    db: DbDep,
) -> DailyInput:
    obj = await _get_or_404(db, entry_id, include_deleted=True)
    if obj.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not deleted")
    old = model_snapshot(obj)
    obj.deleted_at = None
    obj.updated_by = user.id
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=TABLE,
        record_id=obj.id,
        action="restore",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj
