"""eRSV (electronic Receipt of Material) read-only API.

Inbound routes (supply events → daily_inputs), all viewer+ JWT-gated:

- ``GET /ersv/{ersv_number}`` → JSON metadata (no audit log).
- ``GET /ersv/{ersv_number}/html`` → ETag-cached inline HTML preview.
- ``GET /ersv/{ersv_number}/pdf`` → application/pdf download (audited).

Outbound routes (OisteBio → Crown Oil, source = consignment):

- ``GET /ersv/outbound`` → list all outbound declarations (per-PoS row).
- ``GET /ersv/outbound/{consignment_id}/{pos_number}?format=html|pdf`` →
  render outbound eRSV for one (consignment, PoS) pair; allocates
  ``consignment_pos.ersv_outbound_no`` on first call (idempotent thereafter).
  Auth: viewer+.
- ``POST /ersv/outbound/{consignment_id}/{pos_number}/regenerate`` →
  admin-only; force a new ``ersv_outbound_no`` for that PoS and write an
  audit log row.

Numbering format for outbound: ``CO/{yy}/{seq:03d}`` — one number per PoS row
  (cliente direction 2026-05-23: 20 PoS = 20 separate eRSV documents).
  CO  = Colombia (country of dispatch / OisteBio plant)
  yy  = 2-digit year (e.g. "25" for 2025)
  seq = 1-based per-year counter, zero-padded to 3 digits

Path parameter on inbound routes uses the Starlette ``:path`` converter so
the embedded ``/`` in ``NNNNN/YY`` matches without URL-encoding gymnastics.
The ``/html`` and ``/pdf`` suffix routes are registered BEFORE the bare
metadata route so the FastAPI router resolves the more-specific paths first.
Backend then validates ``^\\d{3,5}/\\d{2}$`` on the captured value and
returns 400 on mismatch.

Audit policy: only the PDF routes write to ``audit_log`` (action='insert').
"""

from __future__ import annotations

import re
from datetime import date  # noqa: TC003 — used at runtime by Pydantic model field
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser, ViewerUser  # noqa: TC001 — Annotated deps used at runtime
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.ersv import ErsvDetail
from app.services.ersv_renderer import (
    ConsignmentNotFoundError,
    ErsvNotFoundError,
    InlandShipmentNotFoundError,
    PosNotFoundError,
    fetch_ersv_row,
    is_regenerated,
    render_ersv_inland,
    render_ersv_outbound,
    render_ersv_to_html,
    render_ersv_to_pdf,
)
from app.services.pdf_renderer import PDFRenderError

if TYPE_CHECKING:
    from app.services.ersv_renderer import (
        ErsvHtmlArtifact,
        ErsvInlandHtmlArtifact,
        ErsvInlandPdfArtifact,
        ErsvOutboundHtmlArtifact,
        ErsvOutboundPdfArtifact,
        ErsvRenderArtifact,
    )

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
# Outbound eRSV — Pydantic response schemas
# ---------------------------------------------------------------------------


class OutboundListItem(BaseModel):
    """Single row in the outbound declaration list — one per PoS."""

    model_config = ConfigDict(from_attributes=True)

    consignment_id: int
    code: str
    pos_number: str
    ersv_outbound_no: str | None
    issued_at: date | None  # prod_date_from used as proxy issue date
    off_taker_code: str
    off_taker_name: str
    kg_net: float | None


class RegenerateResponse(BaseModel):
    """Returned by POST /ersv/outbound/{id}/{pos}/regenerate."""

    consignment_id: int
    pos_number: str
    ersv_outbound_no: str
    previous_no: str | None


# ---------------------------------------------------------------------------
# SQL for outbound list
# ---------------------------------------------------------------------------

_LIST_OUTBOUND_SQL = text(
    """
    SELECT
        c.id              AS consignment_id,
        c.code            AS code,
        cp.pos_number     AS pos_number,
        cp.ersv_outbound_no,
        c.prod_date_from  AS issued_at,
        ot.code           AS off_taker_code,
        ot.name           AS off_taker_name,
        CAST(cp.kg_net AS double precision) AS kg_net
    FROM consignment_pos cp
    JOIN consignment c ON c.id = cp.consignment_id
    JOIN off_taker ot ON ot.id = c.off_taker_id
    WHERE c.deleted_at IS NULL
      AND ot.deleted_at IS NULL
      AND cp.deleted_at IS NULL
    ORDER BY c.id DESC, cp.pos_number ASC
    LIMIT :limit OFFSET :offset
    """
)


# ---------------------------------------------------------------------------
# Outbound endpoints — registered BEFORE the greedy inbound :path routes
# ---------------------------------------------------------------------------


@router.get("/outbound", response_model=list[OutboundListItem])
async def list_outbound_declarations(
    _: ViewerUser,
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[dict[str, Any]]:
    """Return a paginated list of all outbound declarations.

    Each item exposes: ``consignment_id``, ``code``, ``ersv_outbound_no``,
    ``issued_at`` (= prod_date_from as proxy), ``off_taker_code``,
    ``off_taker_name``, ``total_kg``.
    """
    offset = (page - 1) * page_size
    result = await db.execute(
        _LIST_OUTBOUND_SQL, {"limit": page_size, "offset": offset}
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/outbound/{consignment_id}/{pos_number}")
async def get_outbound_ersv(
    consignment_id: int,
    pos_number: str,
    _: ViewerUser,
    db: DbDep,
    format: Annotated[str, Query(pattern="^(html|pdf)$")] = "html",
) -> Response:
    """Render the outbound eRSV for a single Proof-of-Sustainability row.

    Cliente direction (2026-05-23): one eRSV per PoS. ``CO/{yy}/{seq:03d}`` is
    minted on first request and persisted on the ``consignment_pos`` row.

    - First call allocates a number and persists it on the PoS row.
    - Subsequent calls return the same number (idempotent).
    - ``?format=html`` (default): returns ``text/html``.
    - ``?format=pdf``: returns ``application/pdf`` (audited to audit_log).
    """
    try:
        artefact = await render_ersv_outbound(
            consignment_id,
            pos_number,
            db,
            format=format,  # type: ignore[arg-type]
        )
    except ConsignmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consignment not found: {consignment_id}",
        ) from exc
    except PosNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"PoS not found: consignment_id={consignment_id} "
                f"pos_number={pos_number}"
            ),
        ) from exc
    except PDFRenderError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF render failed: {exc}",
        ) from exc

    if format == "pdf":
        pdf_artefact: ErsvOutboundPdfArtifact = artefact  # type: ignore[assignment]
        audit = AuditLog(
            table_name="consignment_pos",
            record_id=consignment_id,
            action="insert",
            old_values=None,
            new_values={
                "kind": "ERSV_OUTBOUND_PDF_EXPORT",
                "pos_number": pos_number,
                "ersv_outbound_no": pdf_artefact.ersv_outbound_no,
                "sha256": pdf_artefact.pdf_sha256,
                "page_count": pdf_artefact.page_count,
                "size_bytes": len(pdf_artefact.pdf_bytes),
            },
            changed_by=None,  # ViewerUser dep — user object not captured here
        )
        db.add(audit)
        await db.commit()

        filename = f"ersv_outbound_{pdf_artefact.ersv_outbound_no.replace('/', '_')}.pdf"
        return Response(
            content=pdf_artefact.pdf_bytes,
            media_type="application/pdf",
            headers={
                "Cache-Control": "no-store",
                "X-Content-SHA256": pdf_artefact.pdf_sha256,
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Ersv-Outbound-No": pdf_artefact.ersv_outbound_no,
                "X-Pos-Number": pos_number,
            },
        )

    html_artefact: ErsvOutboundHtmlArtifact = artefact  # type: ignore[assignment]
    return Response(
        content=html_artefact.html,
        media_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "private, max-age=0, must-revalidate",
            "X-Ersv-Outbound-No": html_artefact.ersv_outbound_no,
            "X-Pos-Number": pos_number,
        },
    )


@router.post(
    "/outbound/{consignment_id}/{pos_number}/regenerate",
    response_model=RegenerateResponse,
)
async def regenerate_outbound_number(
    consignment_id: int,
    pos_number: str,
    user: AdminUser,
    db: DbDep,
) -> RegenerateResponse:
    """Admin-only: force-allocate a new ``ersv_outbound_no`` for a PoS row.

    The previous number is permanently replaced. An audit log entry is written
    with ``old_values.ersv_outbound_no`` = previous number so the change is
    traceable. Only admins may call this endpoint.
    """
    # Fetch current state of the PoS row
    result = await db.execute(
        text(
            "SELECT consignment_id, pos_number, ersv_outbound_no "
            "FROM consignment_pos "
            "WHERE consignment_id = :cid AND pos_number = :pos "
            "  AND deleted_at IS NULL"
        ),
        {"cid": consignment_id, "pos": pos_number},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"PoS not found: consignment_id={consignment_id} "
                f"pos_number={pos_number}"
            ),
        )
    previous_no: str | None = row["ersv_outbound_no"]

    try:
        artefact = await render_ersv_outbound(
            consignment_id,
            pos_number,
            db,
            format="html",
            force_new_no=True,
        )
    except ConsignmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consignment not found: {consignment_id}",
        ) from exc
    except PosNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"PoS not found: consignment_id={consignment_id} "
                f"pos_number={pos_number}"
            ),
        ) from exc

    html_artefact: ErsvOutboundHtmlArtifact = artefact  # type: ignore[assignment]
    new_no = html_artefact.ersv_outbound_no

    # Write audit entry — action='update' (changing an existing field value)
    audit = AuditLog(
        table_name="consignment_pos",
        record_id=consignment_id,
        action="update",
        old_values={
            "pos_number": pos_number,
            "ersv_outbound_no": previous_no,
        },
        new_values={
            "kind": "ERSV_OUTBOUND_REGENERATE",
            "pos_number": pos_number,
            "ersv_outbound_no": new_no,
        },
        changed_by=user.id,
    )
    db.add(audit)
    await db.commit()

    return RegenerateResponse(
        consignment_id=consignment_id,
        pos_number=pos_number,
        ersv_outbound_no=new_no,
        previous_no=previous_no,
    )


# ---------------------------------------------------------------------------
# Inland eRSV — Girardot plant → Cartagena Contecar port
# ---------------------------------------------------------------------------


class InlandListItem(BaseModel):
    """Single row in the inland shipment list — one per ISO container."""

    model_config = ConfigDict(from_attributes=True)

    shipment_id: int
    consignment_id: int
    consignment_code: str
    bl_ref: str
    seq_in_bl: int
    container_id: str
    seal_ref: str | None
    load_date: date
    gross_kg: float
    tare_kg: float
    net_kg: float
    ersv_inland_no: str | None


_LIST_INLAND_SQL = text(
    """
    SELECT
        i.id              AS shipment_id,
        i.consignment_id,
        c.code            AS consignment_code,
        i.bl_ref,
        i.seq_in_bl,
        i.container_id,
        i.seal_ref,
        i.load_date,
        CAST(i.gross_kg AS double precision) AS gross_kg,
        CAST(i.tare_kg  AS double precision) AS tare_kg,
        CAST(i.net_kg   AS double precision) AS net_kg,
        i.ersv_inland_no
    FROM inland_shipment i
    JOIN consignment c ON c.id = i.consignment_id
    WHERE i.deleted_at IS NULL
      AND c.deleted_at IS NULL
      AND (CAST(:consignment_id AS bigint) IS NULL
           OR i.consignment_id = CAST(:consignment_id AS bigint))
    ORDER BY i.load_date ASC, i.seq_in_bl ASC, i.id ASC
    LIMIT :limit OFFSET :offset
    """
)


@router.get("/inland", response_model=list[InlandListItem])
async def list_inland_shipments(
    _: ViewerUser,
    db: DbDep,
    consignment_id: Annotated[int | None, Query(ge=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[dict[str, Any]]:
    """Return inland shipments (Girardot → Cartagena), optionally filtered.

    One row per ISO container. Pass ``consignment_id`` to scope to a single
    parent consignment (e.g. all 29 containers of CONS-2025-Q3-CROWN).
    """
    offset = (page - 1) * page_size
    result = await db.execute(
        _LIST_INLAND_SQL,
        {
            "consignment_id": consignment_id,
            "limit": page_size,
            "offset": offset,
        },
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/inland/{shipment_id}")
async def get_inland_ersv(
    shipment_id: int,
    user: ViewerUser,
    db: DbDep,
    format: Annotated[str, Query(pattern="^(html|pdf)$")] = "html",
) -> Response:
    """Render the inland eRSV for one ISO container shipment.

    Numbering ``GIR/{yy}/{DD-MM}/{seq:02d}`` is minted on first call and
    persisted on ``inland_shipment.ersv_inland_no``. Idempotent thereafter.

    - ``?format=html`` (default): inline HTML.
    - ``?format=pdf``: application/pdf (audited).
    """
    try:
        artefact = await render_ersv_inland(
            shipment_id, db, format=format  # type: ignore[arg-type]
        )
    except InlandShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inland shipment not found: {shipment_id}",
        ) from exc
    except PDFRenderError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF render failed: {exc}",
        ) from exc

    if format == "pdf":
        pdf_artefact: ErsvInlandPdfArtifact = artefact  # type: ignore[assignment]
        audit = AuditLog(
            table_name="inland_shipment",
            record_id=shipment_id,
            action="insert",
            old_values=None,
            new_values={
                "kind": "ERSV_INLAND_PDF_EXPORT",
                "ersv_inland_no": pdf_artefact.ersv_inland_no,
                "sha256": pdf_artefact.pdf_sha256,
                "page_count": pdf_artefact.page_count,
                "size_bytes": len(pdf_artefact.pdf_bytes),
            },
            changed_by=user.id,
        )
        db.add(audit)
        await db.commit()

        filename = (
            f"ersv_inland_{pdf_artefact.ersv_inland_no.replace('/', '_')}.pdf"
        )
        return Response(
            content=pdf_artefact.pdf_bytes,
            media_type="application/pdf",
            headers={
                "Cache-Control": "no-store",
                "X-Content-SHA256": pdf_artefact.pdf_sha256,
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Ersv-Inland-No": pdf_artefact.ersv_inland_no,
                "X-Shipment-Id": str(shipment_id),
            },
        )

    html_artefact: ErsvInlandHtmlArtifact = artefact  # type: ignore[assignment]
    return Response(
        content=html_artefact.html,
        media_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "private, max-age=0, must-revalidate",
            "X-Ersv-Inland-No": html_artefact.ersv_inland_no,
            "X-Shipment-Id": str(shipment_id),
        },
    )


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
