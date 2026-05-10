"""Admin endpoints — MV refresh, scheduler status, users CRUD. Admin role only."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit import model_snapshot, write_audit
from app.services.mv_refresh import refresh_all_mvs

router = APIRouter(prefix="/admin", tags=["admin"])
users_router = APIRouter(prefix="/users", tags=["users"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
USERS_TABLE = "users"


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
