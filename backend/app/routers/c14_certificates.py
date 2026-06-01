"""Router for the FMS Appendix A — C14 Laboratory Certificates Log.

Read-only first pass: GET list / GET one / inline PDF preview / audited
download. CRUD/upload deferred. PDF resolved by cert_number under
data/c14/<cert_number>.pdf (bind-mount, no Drive at runtime), mirroring the
product_purchases PDF pattern.
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
from app.models.c14_certificate import C14Certificate
from app.schemas.c14_certificate import C14CertificateRead

DbDep = Annotated[AsyncSession, Depends(get_db)]

router = APIRouter(prefix="/c14-certificates", tags=["c14-certificates"])
TABLE = "c14_certificates"

_C14_PDF_DIR_DEFAULT = Path(__file__).resolve().parents[2] / "data" / "c14"
C14_PDF_DIR = Path(os.environ.get("C14_PDF_DIR", str(_C14_PDF_DIR_DEFAULT)))
_CERT_NUMBER_RE = re.compile(r"^[A-Z0-9_-]{1,40}$")


async def _get_or_404(
    db: AsyncSession, c14_id: int, *, include_deleted: bool = False
) -> C14Certificate:
    stmt = select(C14Certificate).where(C14Certificate.id == c14_id)
    if not include_deleted:
        stmt = stmt.where(C14Certificate.deleted_at.is_(None))
    obj = (await db.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="C14 certificate not found"
        )
    return obj


@router.get("", response_model=list[C14CertificateRead])
async def list_c14_certificates(
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
) -> list[C14Certificate]:
    stmt = select(C14Certificate)
    if not include_deleted:
        stmt = stmt.where(C14Certificate.deleted_at.is_(None))
    stmt = stmt.order_by(
        C14Certificate.period_month.desc(), C14Certificate.cert_number
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{c14_id}", response_model=C14CertificateRead)
async def get_c14_certificate(
    c14_id: int,
    _: ViewerUser,
    db: DbDep,
    include_deleted: bool = Query(False),
) -> C14Certificate:
    return await _get_or_404(db, c14_id, include_deleted=include_deleted)


def _resolve_c14_pdf(cert_number: str) -> Path | None:
    if not _CERT_NUMBER_RE.match(cert_number):
        return None
    candidate = (C14_PDF_DIR / f"{cert_number}.pdf").resolve()
    try:
        candidate.relative_to(C14_PDF_DIR.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


@router.get("/{c14_id}/pdf")
async def get_c14_certificate_pdf(
    c14_id: int,
    _: ViewerUser,
    db: DbDep,
) -> FileResponse:
    """Inline PDF preview for the modal iframe. No audit (viewing != downloading)."""
    obj = await _get_or_404(db, c14_id, include_deleted=True)
    pdf = _resolve_c14_pdf(obj.cert_number)
    if pdf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"C14 certificate PDF not found for {obj.cert_number}",
        )
    return FileResponse(
        path=pdf,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="{obj.cert_number}.pdf"',
        },
    )


@router.get("/{c14_id}/pdf/download")
async def download_c14_certificate_pdf(
    c14_id: int,
    user: ViewerUser,
    db: DbDep,
) -> Response:
    """Audited PDF download (attachment). One audit_log row per download."""
    obj = await _get_or_404(db, c14_id, include_deleted=True)
    pdf = _resolve_c14_pdf(obj.cert_number)
    if pdf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"C14 certificate PDF not found for {obj.cert_number}",
        )
    data = pdf.read_bytes()
    audit = AuditLog(
        table_name=TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values={
            "kind": "C14_CERTIFICATE_PDF_DOWNLOAD",
            "cert_number": obj.cert_number,
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
            "Content-Disposition": f'attachment; filename="{obj.cert_number}.pdf"',
        },
    )
