from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.contract import Contract
from app.schemas.contract import ContractCreate, ContractRead, ContractUpdate

router = APIRouter(prefix="/contracts", tags=["contracts"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=list[ContractRead])
async def list_contracts(
    db: DbDep,
    supplier_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Contract]:
    stmt = select(Contract)
    if supplier_id is not None:
        stmt = stmt.where(Contract.supplier_id == supplier_id)
    stmt = stmt.offset(skip).limit(limit).order_by(Contract.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=ContractRead, status_code=201)
async def create_contract(body: ContractCreate, db: DbDep) -> Contract:
    obj = Contract(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{contract_id}", response_model=ContractRead)
async def get_contract(contract_id: int, db: DbDep) -> Contract:
    obj = await db.get(Contract, contract_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return obj


@router.patch("/{contract_id}", response_model=ContractRead)
async def update_contract(contract_id: int, body: ContractUpdate, db: DbDep) -> Contract:
    obj = await db.get(Contract, contract_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(contract_id: int, db: DbDep) -> None:
    obj = await db.get(Contract, contract_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    await db.delete(obj)
    await db.commit()
