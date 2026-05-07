from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=list[SupplierRead])
async def list_suppliers(
    db: DbDep,
    active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Supplier]:
    stmt = select(Supplier)
    if active is not None:
        stmt = stmt.where(Supplier.active == active)
    stmt = stmt.offset(skip).limit(limit).order_by(Supplier.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=SupplierRead, status_code=201)
async def create_supplier(body: SupplierCreate, db: DbDep) -> Supplier:
    obj = Supplier(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(supplier_id: int, db: DbDep) -> Supplier:
    obj = await db.get(Supplier, supplier_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return obj


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(supplier_id: int, body: SupplierUpdate, db: DbDep) -> Supplier:
    obj = await db.get(Supplier, supplier_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: int, db: DbDep) -> None:
    obj = await db.get(Supplier, supplier_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    obj.active = False
    await db.commit()
