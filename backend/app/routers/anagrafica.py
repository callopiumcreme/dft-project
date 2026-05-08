"""Read-only routers for anagrafica: suppliers, certificates, contracts.

GET-only — no writes (CRUD is out of scope for ingest pipeline).
Excludes soft-deleted rows.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ViewerUser
from app.db.session import get_db
from app.models.certificate import Certificate
from app.models.contract import Contract
from app.models.supplier import Supplier
from app.schemas.certificate import CertificateRead
from app.schemas.contract import ContractRead
from app.schemas.supplier import SupplierRead

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------- SUPPLIERS ----------
suppliers_router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@suppliers_router.get("", response_model=list[SupplierRead])
async def list_suppliers(
    _: ViewerUser,
    db: DbDep,
    active_only: bool = Query(True, description="Filter active=true"),
) -> list[Supplier]:
    stmt = select(Supplier).where(Supplier.deleted_at.is_(None))
    if active_only:
        stmt = stmt.where(Supplier.active.is_(True))
    stmt = stmt.order_by(Supplier.code)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@suppliers_router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(supplier_id: int, _: ViewerUser, db: DbDep) -> Supplier:
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None))
    )
    s = result.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return s


# ---------- CERTIFICATES ----------
certificates_router = APIRouter(prefix="/certificates", tags=["certificates"])


@certificates_router.get("", response_model=list[CertificateRead])
async def list_certificates(
    _: ViewerUser,
    db: DbDep,
    status_filter: str | None = Query(None, alias="status"),
) -> list[Certificate]:
    stmt = select(Certificate).where(Certificate.deleted_at.is_(None))
    if status_filter:
        stmt = stmt.where(Certificate.status == status_filter)
    stmt = stmt.order_by(Certificate.cert_number)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@certificates_router.get("/{cert_id}", response_model=CertificateRead)
async def get_certificate(cert_id: int, _: ViewerUser, db: DbDep) -> Certificate:
    result = await db.execute(
        select(Certificate).where(
            Certificate.id == cert_id, Certificate.deleted_at.is_(None)
        )
    )
    c = result.scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return c


# ---------- CONTRACTS ----------
contracts_router = APIRouter(prefix="/contracts", tags=["contracts"])


@contracts_router.get("", response_model=list[ContractRead])
async def list_contracts(
    _: ViewerUser,
    db: DbDep,
    supplier_id: int | None = Query(None),
) -> list[Contract]:
    stmt = select(Contract).where(Contract.deleted_at.is_(None))
    if supplier_id is not None:
        stmt = stmt.where(Contract.supplier_id == supplier_id)
    stmt = stmt.order_by(Contract.code)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@contracts_router.get("/{contract_id}", response_model=ContractRead)
async def get_contract(contract_id: int, _: ViewerUser, db: DbDep) -> Contract:
    result = await db.execute(
        select(Contract).where(
            Contract.id == contract_id, Contract.deleted_at.is_(None)
        )
    )
    c = result.scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return c
