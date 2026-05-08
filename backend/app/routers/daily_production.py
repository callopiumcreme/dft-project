"""CRUD /daily-production with audit log + soft delete.

- Read: viewer+
- Write: operator+
- Soft delete via deleted_at.
- prod_date is UNIQUE — POST conflicts return 409.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import OperatorUser, ViewerUser
from app.db.session import get_db
from app.models.daily_production import DailyProduction
from app.schemas.daily_production import (
    DailyProductionCreate,
    DailyProductionRead,
    DailyProductionUpdate,
)
from app.services.audit import model_snapshot, write_audit

router = APIRouter(prefix="/daily-production", tags=["daily-production"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
TABLE = "daily_production"


@router.get("", response_model=list[DailyProductionRead])
async def list_daily_production(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    include_deleted: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[DailyProduction]:
    stmt = select(DailyProduction)
    if not include_deleted:
        stmt = stmt.where(DailyProduction.deleted_at.is_(None))
    if date_from is not None:
        stmt = stmt.where(DailyProduction.prod_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyProduction.prod_date <= date_to)
    stmt = stmt.order_by(DailyProduction.prod_date.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/count")
async def count_daily_production(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    include_deleted: bool = Query(False),
) -> dict[str, int]:
    stmt = select(func.count(DailyProduction.id))
    if not include_deleted:
        stmt = stmt.where(DailyProduction.deleted_at.is_(None))
    if date_from is not None:
        stmt = stmt.where(DailyProduction.prod_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyProduction.prod_date <= date_to)
    result = await db.execute(stmt)
    return {"count": int(result.scalar_one())}


async def _get_or_404(
    db: AsyncSession, prod_id: int, *, include_deleted: bool = False
) -> DailyProduction:
    stmt = select(DailyProduction).where(DailyProduction.id == prod_id)
    if not include_deleted:
        stmt = stmt.where(DailyProduction.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DailyProduction not found")
    return obj


@router.get("/{prod_id}", response_model=DailyProductionRead)
async def get_daily_production(
    prod_id: int,
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
) -> DailyProduction:
    return await _get_or_404(db, prod_id, include_deleted=include_deleted)


@router.post("", response_model=DailyProductionRead, status_code=status.HTTP_201_CREATED)
async def create_daily_production(
    body: DailyProductionCreate,
    user: OperatorUser,
    db: DbDep,
) -> DailyProduction:
    obj = DailyProduction(**body.model_dump(), created_by=user.id, updated_by=user.id)
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"DailyProduction for {body.prod_date} already exists",
        )
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


@router.patch("/{prod_id}", response_model=DailyProductionRead)
async def update_daily_production(
    prod_id: int,
    body: DailyProductionUpdate,
    user: OperatorUser,
    db: DbDep,
) -> DailyProduction:
    obj = await _get_or_404(db, prod_id)
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


@router.delete("/{prod_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_daily_production(
    prod_id: int,
    user: OperatorUser,
    db: DbDep,
) -> None:
    obj = await _get_or_404(db, prod_id)
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


@router.post("/{prod_id}/restore", response_model=DailyProductionRead)
async def restore_daily_production(
    prod_id: int,
    user: OperatorUser,
    db: DbDep,
) -> DailyProduction:
    obj = await _get_or_404(db, prod_id, include_deleted=True)
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
