"""Router for Product Purchases: supplier-issued PoS of purchased feedstock.

Read-only first pass: GET list / GET one / inline PDF preview / audited
download. CRUD/upload deferred. PDF resolved by pos_number under
data/pos/<pos_number>.pdf (bind-mount, no Drive at runtime), mirroring the
contracts PDF pattern in anagrafica.py.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ViewerUser
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.product_purchase import ProductPurchase
from app.models.supplier import Supplier
from app.schemas.product_purchase import ProductPurchaseRead

DbDep = Annotated[AsyncSession, Depends(get_db)]

router = APIRouter(prefix="/product-purchases", tags=["product-purchases"])
TABLE = "product_purchases"

_POS_PDF_DIR_DEFAULT = Path(__file__).resolve().parents[2] / "data" / "pos"
POS_PDF_DIR = Path(os.environ.get("POS_PDF_DIR", str(_POS_PDF_DIR_DEFAULT)))
_POS_NUMBER_RE = re.compile(r"^[A-Z0-9_-]{1,40}$")


async def _get_or_404(
    db: AsyncSession, pp_id: int, *, include_deleted: bool = False
) -> ProductPurchase:
    stmt = select(ProductPurchase).where(ProductPurchase.id == pp_id)
    if not include_deleted:
        stmt = stmt.where(ProductPurchase.deleted_at.is_(None))
    obj = (await db.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product purchase not found"
        )
    return obj


def _to_read(obj: ProductPurchase, supplier_name: str | None) -> ProductPurchaseRead:
    read = ProductPurchaseRead.model_validate(obj)
    read.supplier_name = supplier_name
    return read


@router.get("", response_model=list[ProductPurchaseRead])
async def list_product_purchases(
    _: ViewerUser,
    db: DbDep,
    supplier_id: int | None = Query(None),
    include_deleted: bool = Query(False),
) -> list[ProductPurchaseRead]:
    stmt = (
        select(ProductPurchase, Supplier.name)
        .outerjoin(Supplier, Supplier.id == ProductPurchase.supplier_id)
    )
    if not include_deleted:
        stmt = stmt.where(ProductPurchase.deleted_at.is_(None))
    if supplier_id is not None:
        stmt = stmt.where(ProductPurchase.supplier_id == supplier_id)
    stmt = stmt.order_by(ProductPurchase.issuance_date.desc(), ProductPurchase.pos_number)
    rows = (await db.execute(stmt)).all()
    return [_to_read(obj, name) for obj, name in rows]


@router.get("/{pp_id}", response_model=ProductPurchaseRead)
async def get_product_purchase(
    pp_id: int,
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
) -> ProductPurchaseRead:
    obj = await _get_or_404(db, pp_id, include_deleted=include_deleted)
    name = (
        await db.execute(select(Supplier.name).where(Supplier.id == obj.supplier_id))
    ).scalar_one_or_none() if obj.supplier_id is not None else None
    return _to_read(obj, name)


def _resolve_pos_pdf(pos_number: str) -> Path | None:
    if not _POS_NUMBER_RE.match(pos_number):
        return None
    candidate = (POS_PDF_DIR / f"{pos_number}.pdf").resolve()
    try:
        candidate.relative_to(POS_PDF_DIR.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


@router.get("/{pp_id}/pdf")
async def get_product_purchase_pdf(
    pp_id: int,
    _: ViewerUser,
    db: DbDep,
) -> FileResponse:
    """Inline PDF preview for the modal iframe. No audit (viewing != downloading)."""
    obj = await _get_or_404(db, pp_id, include_deleted=True)
    pdf = _resolve_pos_pdf(obj.pos_number)
    if pdf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PoS PDF not found for {obj.pos_number}",
        )
    return FileResponse(
        path=pdf,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="{obj.pos_number}.pdf"',
        },
    )


@router.get("/{pp_id}/pdf/download")
async def download_product_purchase_pdf(
    pp_id: int,
    user: ViewerUser,
    db: DbDep,
) -> Response:
    """Audited PDF download (attachment). One audit_log row per download."""
    obj = await _get_or_404(db, pp_id, include_deleted=True)
    pdf = _resolve_pos_pdf(obj.pos_number)
    if pdf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PoS PDF not found for {obj.pos_number}",
        )
    data = pdf.read_bytes()
    audit = AuditLog(
        table_name=TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values={
            "kind": "PRODUCT_PURCHASE_PDF_DOWNLOAD",
            "pos_number": obj.pos_number,
            "size_bytes": len(data),
        },
        changed_by=user.id,
    )
    db.add(audit)
    await db.commit()
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{obj.pos_number}.pdf"',
        },
    )
