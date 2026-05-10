"""Routers for anagrafica: suppliers (CRUD admin), certificates, contracts (GET).

Suppliers: GET viewer+, POST/PATCH/DELETE admin only with audit log + soft delete.
Certificates / Contracts: GET only (CRUD wired in subsequent tickets).
Excludes soft-deleted rows by default.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser, ViewerUser
from app.db.session import get_db
from app.models.certificate import Certificate
from app.models.contract import Contract
from app.models.supplier import Supplier
from app.schemas.certificate import CertificateCreate, CertificateRead, CertificateUpdate
from app.schemas.contract import ContractCreate, ContractRead, ContractUpdate
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.services.audit import model_snapshot, write_audit

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------- SUPPLIERS ----------
suppliers_router = APIRouter(prefix="/suppliers", tags=["suppliers"])
SUPPLIERS_TABLE = "suppliers"


async def _get_supplier_or_404(
    db: AsyncSession, supplier_id: int, *, include_deleted: bool = False
) -> Supplier:
    stmt = select(Supplier).where(Supplier.id == supplier_id)
    if not include_deleted:
        stmt = stmt.where(Supplier.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return obj


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
async def get_supplier(
    supplier_id: int,
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
) -> Supplier:
    return await _get_supplier_or_404(db, supplier_id, include_deleted=include_deleted)


@suppliers_router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    body: SupplierCreate,
    user: AdminUser,
    db: DbDep,
) -> Supplier:
    obj = Supplier(**body.model_dump())
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Supplier code or name already exists",
        ) from e
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=SUPPLIERS_TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@suppliers_router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    user: AdminUser,
    db: DbDep,
) -> Supplier:
    obj = await _get_supplier_or_404(db, supplier_id)
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
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Supplier code or name already exists",
        ) from e
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=SUPPLIERS_TABLE,
        record_id=obj.id,
        action="update",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@suppliers_router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_supplier(
    supplier_id: int,
    user: AdminUser,
    db: DbDep,
) -> None:
    obj = await _get_supplier_or_404(db, supplier_id)
    old = model_snapshot(obj)
    obj.deleted_at = datetime.utcnow()
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=SUPPLIERS_TABLE,
        record_id=obj.id,
        action="soft_delete",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()


@suppliers_router.post("/{supplier_id}/restore", response_model=SupplierRead)
async def restore_supplier(
    supplier_id: int,
    user: AdminUser,
    db: DbDep,
) -> Supplier:
    obj = await _get_supplier_or_404(db, supplier_id, include_deleted=True)
    if obj.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not deleted"
        )
    old = model_snapshot(obj)
    obj.deleted_at = None
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=SUPPLIERS_TABLE,
        record_id=obj.id,
        action="restore",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


# ---------- CERTIFICATES ----------
certificates_router = APIRouter(prefix="/certificates", tags=["certificates"])
CERTIFICATES_TABLE = "certificates"


async def _get_certificate_or_404(
    db: AsyncSession, cert_id: int, *, include_deleted: bool = False
) -> Certificate:
    stmt = select(Certificate).where(Certificate.id == cert_id)
    if not include_deleted:
        stmt = stmt.where(Certificate.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    return obj


async def _resolve_suppliers(db: AsyncSession, ids: list[int]) -> list[Supplier]:
    if not ids:
        return []
    stmt = select(Supplier).where(Supplier.id.in_(ids), Supplier.deleted_at.is_(None))
    result = await db.execute(stmt)
    found = list(result.scalars().all())
    if len(found) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more supplier_ids invalid",
        )
    return found


@certificates_router.get("", response_model=list[CertificateRead])
async def list_certificates(
    _: ViewerUser,
    db: DbDep,
    status_filter: str | None = Query(None, alias="status"),
    include_deleted: bool = Query(False),
) -> list[Certificate]:
    stmt = select(Certificate)
    if not include_deleted:
        stmt = stmt.where(Certificate.deleted_at.is_(None))
    if status_filter:
        stmt = stmt.where(Certificate.status == status_filter)
    stmt = stmt.order_by(Certificate.cert_number)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@certificates_router.get("/{cert_id}", response_model=CertificateRead)
async def get_certificate(
    cert_id: int,
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
) -> Certificate:
    return await _get_certificate_or_404(db, cert_id, include_deleted=include_deleted)


@certificates_router.post("", response_model=CertificateRead, status_code=status.HTTP_201_CREATED)
async def create_certificate(
    body: CertificateCreate,
    user: AdminUser,
    db: DbDep,
) -> Certificate:
    payload = body.model_dump()
    supplier_ids = payload.pop("supplier_ids", []) or []
    obj = Certificate(**payload)
    if supplier_ids:
        obj.suppliers = await _resolve_suppliers(db, supplier_ids)
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate number already exists",
        ) from e
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=CERTIFICATES_TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@certificates_router.patch("/{cert_id}", response_model=CertificateRead)
async def update_certificate(
    cert_id: int,
    body: CertificateUpdate,
    user: AdminUser,
    db: DbDep,
) -> Certificate:
    obj = await _get_certificate_or_404(db, cert_id)
    old = model_snapshot(obj)
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )
    supplier_ids = patch.pop("supplier_ids", None)
    for k, v in patch.items():
        setattr(obj, k, v)
    if supplier_ids is not None:
        obj.suppliers = await _resolve_suppliers(db, supplier_ids)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate number already exists",
        ) from e
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=CERTIFICATES_TABLE,
        record_id=obj.id,
        action="update",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@certificates_router.delete("/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_certificate(
    cert_id: int,
    user: AdminUser,
    db: DbDep,
) -> None:
    obj = await _get_certificate_or_404(db, cert_id)
    old = model_snapshot(obj)
    obj.deleted_at = datetime.utcnow()
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=CERTIFICATES_TABLE,
        record_id=obj.id,
        action="soft_delete",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()


@certificates_router.post("/{cert_id}/restore", response_model=CertificateRead)
async def restore_certificate(
    cert_id: int,
    user: AdminUser,
    db: DbDep,
) -> Certificate:
    obj = await _get_certificate_or_404(db, cert_id, include_deleted=True)
    if obj.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not deleted"
        )
    old = model_snapshot(obj)
    obj.deleted_at = None
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=CERTIFICATES_TABLE,
        record_id=obj.id,
        action="restore",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


# ---------- CONTRACTS ----------
contracts_router = APIRouter(prefix="/contracts", tags=["contracts"])
CONTRACTS_TABLE = "contracts"


async def _get_contract_or_404(
    db: AsyncSession, contract_id: int, *, include_deleted: bool = False
) -> Contract:
    stmt = select(Contract).where(Contract.id == contract_id)
    if not include_deleted:
        stmt = stmt.where(Contract.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return obj


@contracts_router.get("", response_model=list[ContractRead])
async def list_contracts(
    _: ViewerUser,
    db: DbDep,
    supplier_id: int | None = Query(None),
    include_deleted: bool = Query(False),
) -> list[Contract]:
    stmt = select(Contract)
    if not include_deleted:
        stmt = stmt.where(Contract.deleted_at.is_(None))
    if supplier_id is not None:
        stmt = stmt.where(Contract.supplier_id == supplier_id)
    stmt = stmt.order_by(Contract.code)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@contracts_router.get("/{contract_id}", response_model=ContractRead)
async def get_contract(
    contract_id: int,
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
) -> Contract:
    return await _get_contract_or_404(db, contract_id, include_deleted=include_deleted)


@contracts_router.post("", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
async def create_contract(
    body: ContractCreate,
    user: AdminUser,
    db: DbDep,
) -> Contract:
    obj = Contract(**body.model_dump())
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contract code already exists or supplier not found",
        ) from e
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=CONTRACTS_TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@contracts_router.patch("/{contract_id}", response_model=ContractRead)
async def update_contract(
    contract_id: int,
    body: ContractUpdate,
    user: AdminUser,
    db: DbDep,
) -> Contract:
    obj = await _get_contract_or_404(db, contract_id)
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
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contract code already exists or supplier not found",
        ) from e
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=CONTRACTS_TABLE,
        record_id=obj.id,
        action="update",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@contracts_router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_contract(
    contract_id: int,
    user: AdminUser,
    db: DbDep,
) -> None:
    obj = await _get_contract_or_404(db, contract_id)
    old = model_snapshot(obj)
    obj.deleted_at = datetime.utcnow()
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=CONTRACTS_TABLE,
        record_id=obj.id,
        action="soft_delete",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()


@contracts_router.post("/{contract_id}/restore", response_model=ContractRead)
async def restore_contract(
    contract_id: int,
    user: AdminUser,
    db: DbDep,
) -> Contract:
    obj = await _get_contract_or_404(db, contract_id, include_deleted=True)
    if obj.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not deleted"
        )
    old = model_snapshot(obj)
    obj.deleted_at = None
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=CONTRACTS_TABLE,
        record_id=obj.id,
        action="restore",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj
