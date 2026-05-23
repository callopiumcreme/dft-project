"""Router: off_taker — CRUD for buyer entities (Crown Oil and future buyers).

Auth: all reads require viewer+; writes require operator+; delete requires admin.
Audit: insert / update / soft_delete written to audit_log for every mutation.
Soft delete: DELETE sets deleted_at = NOW(), never removes DB row.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser, ViewerUser
from app.db.session import get_db
from app.models.off_taker import OffTaker
from app.schemas.logistics import OffTakerCreate, OffTakerOut, OffTakerUpdate
from app.services.audit import model_snapshot, write_audit

router = APIRouter(prefix="/off-takers", tags=["off-takers"])
DbDep = Annotated[AsyncSession, Depends(get_db)]

_TABLE = "off_taker"


async def _get_or_404(
    db: AsyncSession,
    off_taker_id: int,
    *,
    include_deleted: bool = False,
) -> OffTaker:
    stmt = select(OffTaker).where(OffTaker.id == off_taker_id)
    if not include_deleted:
        stmt = stmt.where(OffTaker.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OffTaker not found")
    return obj


@router.get("", response_model=list[OffTakerOut])
async def list_off_takers(
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[OffTaker]:
    """List all off-takers. Excludes soft-deleted rows by default."""
    stmt = select(OffTaker)
    if not include_deleted:
        stmt = stmt.where(OffTaker.deleted_at.is_(None))
    stmt = stmt.order_by(OffTaker.code).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=OffTakerOut, status_code=status.HTTP_201_CREATED)
async def create_off_taker(
    body: OffTakerCreate,
    user: AdminUser,
    db: DbDep,
) -> OffTaker:
    """Create a new off-taker. Admin only."""
    obj = OffTaker(**body.model_dump())
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OffTaker code already exists or FK invalid",
        ) from exc
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{off_taker_id}", response_model=OffTakerOut)
async def get_off_taker(
    off_taker_id: int,
    _: ViewerUser,
    db: DbDep,
) -> OffTaker:
    """Retrieve a single off-taker by ID."""
    return await _get_or_404(db, off_taker_id)


@router.patch("/{off_taker_id}", response_model=OffTakerOut)
async def update_off_taker(
    off_taker_id: int,
    body: OffTakerUpdate,
    user: AdminUser,
    db: DbDep,
) -> OffTaker:
    """Partial update. Admin only."""
    obj = await _get_or_404(db, off_taker_id)
    old = model_snapshot(obj)
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )
    for k, v in patch.items():
        setattr(obj, k, v)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OffTaker code already exists or FK invalid",
        ) from exc
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_TABLE,
        record_id=obj.id,
        action="update",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{off_taker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_off_taker(
    off_taker_id: int,
    user: AdminUser,
    db: DbDep,
) -> None:
    """Soft delete (sets deleted_at). Admin only. DB row is never removed."""
    obj = await _get_or_404(db, off_taker_id)
    old = model_snapshot(obj)
    obj.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_TABLE,
        record_id=obj.id,
        action="soft_delete",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
