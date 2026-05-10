"""Admin endpoints — MV refresh, scheduler status, users CRUD, audit log. Admin role only."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit import model_snapshot, write_audit
from app.services.mv_refresh import refresh_all_mvs

router = APIRouter(prefix="/admin", tags=["admin"])
users_router = APIRouter(prefix="/users", tags=["users"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
USERS_TABLE = "users"

AuditAction = Literal["insert", "update", "delete", "soft_delete", "restore"]


@router.post("/refresh-mvs")
async def refresh_mvs(_: AdminUser) -> dict[str, dict[str, str]]:
    results = await refresh_all_mvs()
    return {"refreshed": results}


def _safe_snapshot(obj: User) -> dict[str, Any]:
    snap = model_snapshot(obj)
    snap.pop("password_hash", None)
    return snap


async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="User not found")
    return obj


def _validate_password(pw: str) -> None:
    if len(pw) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    if len(pw.encode("utf-8")) > 72:
        raise HTTPException(status_code=422, detail="Password too long (max 72 bytes)")


@users_router.get("", response_model=list[UserRead])
async def list_users(
    _: AdminUser,
    db: DbDep,
    active_only: bool = Query(default=False),
    role: str | None = Query(default=None),
) -> list[User]:
    stmt = select(User).order_by(User.id.desc())
    if active_only:
        stmt = stmt.where(User.active.is_(True))
    if role:
        stmt = stmt.where(User.role == role)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@users_router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, _: AdminUser, db: DbDep) -> User:
    return await _get_user_or_404(db, user_id)


@users_router.post("", response_model=UserRead, status_code=201)
async def create_user(body: UserCreate, user: AdminUser, db: DbDep) -> User:
    _validate_password(body.password)
    obj = User(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        active=body.active,
        password_hash=hash_password(body.password),
    )
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists") from e
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=USERS_TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values=_safe_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@users_router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    body: UserUpdate,
    user: AdminUser,
    db: DbDep,
) -> User:
    obj = await _get_user_or_404(db, user_id)
    old = _safe_snapshot(obj)

    patch = body.model_dump(exclude_unset=True)
    new_password = patch.pop("password", None)

    is_self = obj.id == user.id
    if is_self and "active" in patch and patch["active"] is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    if is_self and "role" in patch and patch["role"] != obj.role:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    for k, v in patch.items():
        setattr(obj, k, v)

    if new_password is not None:
        _validate_password(new_password)
        obj.password_hash = hash_password(new_password)

    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists") from e
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=USERS_TABLE,
        record_id=obj.id,
        action="update",
        old_values=old,
        new_values=_safe_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@users_router.delete("/{user_id}", status_code=204)
async def deactivate_user(user_id: int, user: AdminUser, db: DbDep) -> None:
    obj = await _get_user_or_404(db, user_id)
    if obj.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    if not obj.active:
        return None
    old = _safe_snapshot(obj)
    obj.active = False
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=USERS_TABLE,
        record_id=obj.id,
        action="soft_delete",
        old_values=old,
        new_values=_safe_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    return None


@users_router.post("/{user_id}/restore", response_model=UserRead)
async def reactivate_user(user_id: int, user: AdminUser, db: DbDep) -> User:
    obj = await _get_user_or_404(db, user_id)
    if obj.active:
        return obj
    old = _safe_snapshot(obj)
    obj.active = True
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=USERS_TABLE,
        record_id=obj.id,
        action="restore",
        old_values=old,
        new_values=_safe_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


class AuditLogEntry(AuditLogRead):
    changed_by_email: str | None = None


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


@router.get("/audit-log/tables", response_model=list[str])
async def list_audit_tables(_: AdminUser, db: DbDep) -> list[str]:
    stmt = select(AuditLog.table_name).distinct().order_by(AuditLog.table_name)
    result = await db.execute(stmt)
    return [r[0] for r in result.all()]


@router.get("/audit-log", response_model=AuditLogPage)
async def list_audit_log(
    _: AdminUser,
    db: DbDep,
    table_name: str | None = Query(default=None),
    record_id: int | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    changed_by: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> AuditLogPage:
    base = select(AuditLog).order_by(AuditLog.changed_at.desc(), AuditLog.id.desc())
    count_base = select(func.count()).select_from(AuditLog)

    filters = []
    if table_name:
        filters.append(AuditLog.table_name == table_name)
    if record_id is not None:
        filters.append(AuditLog.record_id == record_id)
    if action:
        filters.append(AuditLog.action == action)
    if changed_by is not None:
        filters.append(AuditLog.changed_by == changed_by)
    if date_from:
        filters.append(
            AuditLog.changed_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to:
        filters.append(
            AuditLog.changed_at
            < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )

    for f in filters:
        base = base.where(f)
        count_base = count_base.where(f)

    total_res = await db.execute(count_base)
    total = int(total_res.scalar_one())

    rows_res = await db.execute(base.limit(limit).offset(offset))
    rows = list(rows_res.scalars().all())

    user_ids = {r.changed_by for r in rows if r.changed_by is not None}
    email_map: dict[int, str] = {}
    if user_ids:
        u_res = await db.execute(select(User.id, User.email).where(User.id.in_(user_ids)))
        email_map = {uid: em for uid, em in u_res.all()}

    items = [
        AuditLogEntry(
            id=r.id,
            table_name=r.table_name,
            record_id=r.record_id,
            action=r.action,
            old_values=r.old_values,
            new_values=r.new_values,
            changed_by=r.changed_by,
            changed_at=r.changed_at,
            changed_by_email=email_map.get(r.changed_by) if r.changed_by else None,
        )
        for r in rows
    ]
    return AuditLogPage(items=items, total=total, limit=limit, offset=offset)
