from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.certificate import Certificate
from app.schemas.certificate import CertificateCreate, CertificateRead, CertificateUpdate

router = APIRouter(prefix="/certificates", tags=["certificates"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=list[CertificateRead])
async def list_certificates(
    db: DbDep,
    supplier_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Certificate]:
    stmt = select(Certificate)
    if supplier_id is not None:
        stmt = stmt.where(Certificate.supplier_id == supplier_id)
    if status is not None:
        stmt = stmt.where(Certificate.status == status)
    stmt = stmt.offset(skip).limit(limit).order_by(Certificate.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=CertificateRead, status_code=201)
async def create_certificate(body: CertificateCreate, db: DbDep) -> Certificate:
    obj = Certificate(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{certificate_id}", response_model=CertificateRead)
async def get_certificate(certificate_id: int, db: DbDep) -> Certificate:
    obj = await db.get(Certificate, certificate_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return obj


@router.patch("/{certificate_id}", response_model=CertificateRead)
async def update_certificate(
    certificate_id: int, body: CertificateUpdate, db: DbDep
) -> Certificate:
    obj = await db.get(Certificate, certificate_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{certificate_id}", status_code=204)
async def delete_certificate(certificate_id: int, db: DbDep) -> None:
    obj = await db.get(Certificate, certificate_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    await db.delete(obj)
    await db.commit()
