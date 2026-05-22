"""eRSV (electronic Receipt of Material) read-only API.

Three routes, all viewer+ JWT-gated:

- ``GET /ersv/{ersv_number}`` → JSON metadata (no audit log).
- ``GET /ersv/{ersv_number}/html`` → ETag-cached inline HTML preview
  for the in-browser viewer.
- ``GET /ersv/{ersv_number}/pdf`` → application/pdf download, with
  an ``audit_log`` row inserted on every successful render.

The path parameter uses the Starlette ``:path`` converter so the embedded
``/`` in ``NNNNN/YY`` matches without URL-encoding gymnastics. The
``/html`` and ``/pdf`` suffix routes are registered BEFORE the bare
metadata route so the FastAPI router resolves the more-specific paths
first (greedy ``:path`` would otherwise swallow ``/html`` and ``/pdf``).
Backend then validates ``^\\d{3,5}/\\d{2}$`` on the captured value and
returns 400 on mismatch.

Audit policy (per W2 plan): only the PDF route writes to ``audit_log``,
using ``action='insert'`` (the CHECK constraint forbids ``export``;
``insert`` is the canonical "create this artefact" action used by the
existing ``/reports/mass-balance/export`` route).

The ``/pdf`` route sets ``Cache-Control: no-store`` because every render
is audited and the artefact must not be served from a shared cache. The
``/html`` route emits a weak ETag derived from
``(ersv_number, updated_at, rectified_at)`` — stable across renders of
the same row — and respects ``If-None-Match`` with a 304 short-circuit.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ViewerUser  # noqa: TC001 — Annotated dep used at runtime
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.ersv import ErsvDetail
from app.services.ersv_renderer import (
    ErsvNotFoundError,
    fetch_ersv_row,
    is_regenerated,
    render_ersv_to_html,
    render_ersv_to_pdf,
)
from app.services.pdf_renderer import PDFRenderError

if TYPE_CHECKING:
    from app.services.ersv_renderer import ErsvHtmlArtifact, ErsvRenderArtifact

router = APIRouter(prefix="/ersv", tags=["ersv"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_ERSV_RE = re.compile(r"^\d{3,5}/\d{2}$")


def _validate_ersv_number(ersv_number: str) -> str:
    """Validate path-param against ``NNN/YY`` … ``NNNNN/YY`` — 400 on mismatch."""
    if not _ERSV_RE.match(ersv_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "ersv_number must match ^\\d{3,5}/\\d{2}$ "
                "(e.g. 153/25 or 00042/25)."
            ),
        )
    return ersv_number


def _filename_for(ersv_number: str) -> str:
    """File-system-safe filename — slash → underscore."""
    return f"ersv_{ersv_number.replace('/', '_')}.pdf"


# ---------------------------------------------------------------------------
# HTML preview (ETag-cached, no audit) — registered FIRST so the more-specific
# /html suffix matches before the greedy :path route below.
# ---------------------------------------------------------------------------
@router.get("/{ersv_number:path}/html")
async def get_ersv_html(
    ersv_number: str,
    request: Request,
    _: ViewerUser,
    db: DbDep,
    daily_input_id: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    _validate_ersv_number(ersv_number)
    try:
        artefact: ErsvHtmlArtifact = await render_ersv_to_html(
            db, ersv_number, daily_input_id=daily_input_id
        )
    except ErsvNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"eRSV not found: {ersv_number}",
        ) from exc

    inm = request.headers.get("if-none-match")
    if inm is not None and inm == artefact.etag:
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={
                "ETag": artefact.etag,
                "Cache-Control": "private, max-age=0, must-revalidate",
            },
        )

    return Response(
        content=artefact.html,
        media_type="text/html; charset=utf-8",
        headers={
            "ETag": artefact.etag,
            "Cache-Control": "private, max-age=0, must-revalidate",
        },
    )


# ---------------------------------------------------------------------------
# PDF download (audited, no-store) — also registered before the bare metadata
# route so the /pdf suffix wins over the greedy :path match.
# ---------------------------------------------------------------------------
@router.get("/{ersv_number:path}/pdf")
async def get_ersv_pdf(
    ersv_number: str,
    user: ViewerUser,
    db: DbDep,
    daily_input_id: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    _validate_ersv_number(ersv_number)
    try:
        artefact: ErsvRenderArtifact = await render_ersv_to_pdf(
            db, ersv_number, daily_input_id=daily_input_id
        )
    except ErsvNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"eRSV not found: {ersv_number}",
        ) from exc
    except PDFRenderError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF render failed: {exc}",
        ) from exc

    audit = AuditLog(
        table_name="ersv",
        record_id=artefact.daily_input_id,
        action="insert",
        old_values=None,
        new_values={
            "kind": "ERSV_PDF_EXPORT",
            "ersv_number": artefact.ersv_number,
            "sha256": artefact.pdf_sha256,
            "page_count": artefact.page_count,
            "size_bytes": len(artefact.pdf_bytes),
        },
        changed_by=user.id,
    )
    db.add(audit)
    await db.commit()

    filename = _filename_for(artefact.ersv_number)
    return Response(
        content=artefact.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "X-Content-SHA256": artefact.pdf_sha256,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# JSON metadata — greedy :path route registered LAST so /html and /pdf above
# take precedence during FastAPI route resolution.
# ---------------------------------------------------------------------------
@router.get("/{ersv_number:path}", response_model=ErsvDetail)
async def get_ersv_metadata(
    ersv_number: str,
    _: ViewerUser,
    db: DbDep,
    daily_input_id: Annotated[int | None, Query(ge=1)] = None,
) -> ErsvDetail:
    """Return JSON metadata for a single eRSV — no audit log, no render."""
    _validate_ersv_number(ersv_number)
    try:
        row = await fetch_ersv_row(db, ersv_number, daily_input_id=daily_input_id)
    except ErsvNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"eRSV not found: {ersv_number}",
        ) from exc

    return ErsvDetail(
        ersv_number=row["ersv_number"],
        daily_input_id=int(row["id"]),
        entry_date=row["entry_date"],
        entry_time=row["entry_time"],
        supplier_id=int(row["supplier_id"]),
        supplier_code=row["supplier_code"],
        supplier_name=row["supplier_name"],
        total_input_kg=row["total_input_kg"],
        car_kg=row["car_kg"],
        truck_kg=row["truck_kg"],
        special_kg=row["special_kg"],
        cert_iscc_ref=row["cert_iscc_ref"],
        is_regenerated=is_regenerated(row["original_values"]),
        rectified_at=row["rectified_at"],
        rectification_reason=row["rectification_reason"],
        updated_at=row["updated_at"],
    )
