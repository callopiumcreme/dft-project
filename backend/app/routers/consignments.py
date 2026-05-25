"""Router: consignments + consignment_pos + consignment_production_link.

Auth: reads require viewer+; POST/PATCH require operator+; DELETE requires admin.
Audit: insert / update / soft_delete written to audit_log.
Soft delete: DELETE /consignments/{id} sets deleted_at = NOW().
No audit on consignment_pos / consignment_production_link (association rows —
  noise-reduction decision; documented here intentionally).
"""
from __future__ import annotations

import os
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import AdminUser, OperatorUser, ViewerUser
from app.db.session import get_db
from sqlalchemy import text as sa_text
from app.models.consignment import Consignment
from app.models.consignment_pos import ConsignmentPos
from app.models.consignment_pos_customs import ConsignmentPosCustoms
from app.models.consignment_production_link import ConsignmentProductionLink
from app.models.off_taker import OffTaker
from app.models.shipment_leg import ShipmentLeg
from app.models.shipment_unit import ShipmentUnit
from app.schemas.logistics import (
    ConsignmentCreate,
    ConsignmentDetail,
    ConsignmentOut,
    ConsignmentPosCreate,
    ConsignmentPosCustomsOut,
    ConsignmentPosOut,
    ConsignmentProductionLinkCreate,
    ConsignmentProductionLinkOut,
    ConsignmentSummary,
    ConsignmentUpdate,
    OffTakerOut,
    ShipmentLegDetail,
    ShipmentUnitOut,
)
from app.services.audit import model_snapshot, write_audit

router = APIRouter(prefix="/consignments", tags=["consignments"])
DbDep = Annotated[AsyncSession, Depends(get_db)]

_TABLE = "consignment"


async def _get_or_404(
    db: AsyncSession,
    consignment_id: int,
    *,
    include_deleted: bool = False,
) -> Consignment:
    stmt = select(Consignment).where(Consignment.id == consignment_id)
    if not include_deleted:
        stmt = stmt.where(Consignment.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Consignment not found"
        )
    return obj


@router.get("", response_model=list[ConsignmentSummary])
async def list_consignments(
    _: ViewerUser,
    db: DbDep,
    off_taker_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    prod_date_from: date | None = Query(None),
    prod_date_to: date | None = Query(None),
    include_deleted: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[ConsignmentSummary]:
    """List consignments with optional filters on off_taker, status, and production date range.

    Response shape: ConsignmentSummary — nested off_taker + chain-derived KPI fields
    (kg_residual_utb from UTB transload leg.kg_stock_residual, kg_delivered_uk from
    delivery_uk leg.kg_out). Eager-loads off_taker to avoid N+1 / async lazy-load None.
    """
    stmt = select(Consignment).options(selectinload(Consignment.off_taker))
    if not include_deleted:
        stmt = stmt.where(Consignment.deleted_at.is_(None))
    if off_taker_id is not None:
        stmt = stmt.where(Consignment.off_taker_id == off_taker_id)
    if status_filter is not None:
        stmt = stmt.where(Consignment.status == status_filter)
    if prod_date_from is not None:
        stmt = stmt.where(
            (Consignment.prod_date_to >= prod_date_from) | Consignment.prod_date_to.is_(None)
        )
    if prod_date_to is not None:
        stmt = stmt.where(
            (Consignment.prod_date_from <= prod_date_to) | Consignment.prod_date_from.is_(None)
        )
    stmt = stmt.order_by(Consignment.code).offset(skip).limit(limit)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    # KPI aggregates per consignment_id — single query, grouped
    if rows:
        ids = [r.id for r in rows]
        kpi_stmt = (
            select(
                ShipmentLeg.consignment_id,
                func.sum(
                    func.coalesce(
                        ShipmentLeg.kg_stock_residual,
                        0,
                    )
                ).filter(ShipmentLeg.leg_type == "utb_transload").label("kg_residual_utb"),
                func.sum(
                    func.coalesce(ShipmentLeg.kg_out, 0)
                ).filter(ShipmentLeg.leg_type == "delivery_uk").label("kg_delivered_uk"),
            )
            .where(ShipmentLeg.consignment_id.in_(ids))
            .group_by(ShipmentLeg.consignment_id)
        )
        kpi_result = await db.execute(kpi_stmt)
        kpi_by_id: dict[int, tuple[Decimal | None, Decimal | None]] = {
            cid: (residual, delivered) for cid, residual, delivered in kpi_result.all()
        }
    else:
        kpi_by_id = {}

    return [
        ConsignmentSummary.model_validate(
            {
                **{c.name: getattr(r, c.name) for c in r.__table__.columns},
                "off_taker": (
                    OffTakerOut.model_validate(r.off_taker) if r.off_taker else None
                ),
                "kg_residual_utb": kpi_by_id.get(r.id, (None, None))[0],
                "kg_delivered_uk": kpi_by_id.get(r.id, (None, None))[1],
            }
        )
        for r in rows
    ]


@router.post("", response_model=ConsignmentOut, status_code=status.HTTP_201_CREATED)
async def create_consignment(
    body: ConsignmentCreate,
    user: OperatorUser,
    db: DbDep,
) -> Consignment:
    """Create a new consignment. Operator+ required."""
    obj = Consignment(**body.model_dump())
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consignment code already exists or off_taker_id not found",
        ) from exc
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{consignment_id}", response_model=ConsignmentDetail)
async def get_consignment_detail(
    consignment_id: int,
    _: ViewerUser,
    db: DbDep,
) -> ConsignmentDetail:
    """Return full ConsignmentDetail: consignment + off_taker + legs (with units) + pos + links.

    This is the primary endpoint consumed by #3 logistics-ui for the chain-of-custody detail page.
    """
    obj = await _get_or_404(db, consignment_id)

    # Off-taker
    off_taker_row = None
    if obj.off_taker_id:
        ot_result = await db.execute(
            select(OffTaker).where(OffTaker.id == obj.off_taker_id)
        )
        ot = ot_result.scalar_one_or_none()
        if ot is not None:
            off_taker_row = OffTakerOut.model_validate(ot)

    # Legs (active only — no deleted legs in detail)
    legs_result = await db.execute(
        select(ShipmentLeg)
        .where(
            ShipmentLeg.consignment_id == consignment_id,
            ShipmentLeg.deleted_at.is_(None),
        )
        .order_by(ShipmentLeg.seq)
    )
    legs = list(legs_result.scalars().all())

    # Units per leg
    leg_details: list[ShipmentLegDetail] = []
    for leg in legs:
        units_result = await db.execute(
            select(ShipmentUnit)
            .where(ShipmentUnit.leg_id == leg.id)
            .order_by(ShipmentUnit.id)
        )
        units = [ShipmentUnitOut.model_validate(u) for u in units_result.scalars().all()]
        leg_detail = ShipmentLegDetail(
            **{k: getattr(leg, k) for k in ShipmentLegDetail.model_fields if k != "units"},
            units=units,
        )
        leg_details.append(leg_detail)

    # PoS (active only — soft-deleted rows hidden from detail view)
    pos_result = await db.execute(
        select(ConsignmentPos)
        .where(
            ConsignmentPos.consignment_id == consignment_id,
            ConsignmentPos.deleted_at.is_(None),
        )
        .order_by(ConsignmentPos.pos_number)
    )
    pos_list = [ConsignmentPosOut.model_validate(p) for p in pos_result.scalars().all()]

    # Production links
    links_result = await db.execute(
        select(ConsignmentProductionLink)
        .where(ConsignmentProductionLink.consignment_id == consignment_id)
        .order_by(ConsignmentProductionLink.prod_date)
    )
    links = [
        ConsignmentProductionLinkOut.model_validate(lk)
        for lk in links_result.scalars().all()
    ]

    # Customs (EAD) records — 1:1 with PoS, ordered by issuing_date.
    customs_result = await db.execute(
        select(ConsignmentPosCustoms)
        .where(
            ConsignmentPosCustoms.consignment_id == consignment_id,
            ConsignmentPosCustoms.deleted_at.is_(None),
        )
        .order_by(ConsignmentPosCustoms.issuing_date, ConsignmentPosCustoms.pos_number)
    )
    customs_list = [
        ConsignmentPosCustomsOut.model_validate(c)
        for c in customs_result.scalars().all()
    ]

    base = ConsignmentOut.model_validate(obj)
    return ConsignmentDetail(
        **base.model_dump(),
        off_taker=off_taker_row,
        legs=leg_details,
        pos=pos_list,
        production_links=links,
        customs=customs_list,
    )


@router.get("/{consignment_id}/chain-summary")
async def get_chain_summary(
    consignment_id: int,
    _: ViewerUser,
    db: DbDep,
) -> dict:
    """Read-only chain-of-custody aggregate from ``v_chain_summary``.

    Returned shape is a flat dict (the view's columns) with Decimals
    serialised as strings via FastAPI's default JSON encoder. Powers the
    ``/app/logistics/[id]`` widget rendered above Chain of custody.

    See docs/mass-balance-allocation-policy.md for the allocation rule
    that drives the upstream / downstream counts in this payload.
    """
    # Verify consignment exists (404 surface — view returns 0 rows for
    # soft-deleted or missing consignment).
    await _get_or_404(db, consignment_id)

    result = await db.execute(
        sa_text("SELECT * FROM v_chain_summary WHERE consignment_id = :cid"),
        {"cid": consignment_id},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chain summary unavailable",
        )
    # Decimal → str so the response is stable across client parsers.
    return {
        k: (str(v) if isinstance(v, Decimal) else v)
        for k, v in dict(row).items()
    }


@router.patch("/{consignment_id}", response_model=ConsignmentOut)
async def update_consignment(
    consignment_id: int,
    body: ConsignmentUpdate,
    user: OperatorUser,
    db: DbDep,
) -> Consignment:
    """Partial update. Operator+ required.

    Status override: any authenticated operator+ may set any status value.
    Admin-only status gate is not enforced here — the UI controls access by
    showing the status field only to admins (see locked decision Q8).
    """
    obj = await _get_or_404(db, consignment_id)
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
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consignment code already exists or FK invalid",
        ) from exc
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_TABLE,
        record_id=obj.id,
        action="update",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{consignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_consignment(
    consignment_id: int,
    user: AdminUser,
    db: DbDep,
) -> None:
    """Soft delete (sets deleted_at = NOW()). Admin only. DB row is never removed."""
    obj = await _get_or_404(db, consignment_id)
    old = model_snapshot(obj)
    obj.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_TABLE,
        record_id=obj.id,
        action="soft_delete",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Customs (EAD) sub-resource — PDF streaming
# ---------------------------------------------------------------------------


_CUSTOMS_ROOT = Path(os.environ.get("CUSTOMS_ROOT", "/data/customs"))
# MRN format on Dutch DMS export: 18 chars, alphanumeric uppercase
# (e.g. `25NL00021BHA22GMD8`). Anchor strictly to prevent path-traversal.
_MRN_RE = re.compile(r"^[0-9A-Z]{18}$")


@router.get(
    "/{consignment_id}/customs",
    response_model=list[ConsignmentPosCustomsOut],
)
async def list_consignment_customs(
    consignment_id: int,
    _: ViewerUser,
    db: DbDep,
) -> list[ConsignmentPosCustomsOut]:
    """List EAD customs records attached to this consignment.

    Same data also embedded in ConsignmentDetail.customs — this endpoint
    exists for standalone use (e.g. customs-only screens).
    """
    await _get_or_404(db, consignment_id)
    rows = await db.execute(
        select(ConsignmentPosCustoms)
        .where(
            ConsignmentPosCustoms.consignment_id == consignment_id,
            ConsignmentPosCustoms.deleted_at.is_(None),
        )
        .order_by(ConsignmentPosCustoms.issuing_date, ConsignmentPosCustoms.pos_number)
    )
    return [ConsignmentPosCustomsOut.model_validate(c) for c in rows.scalars().all()]


@router.get("/{consignment_id}/customs/{mrn}.pdf")
async def stream_customs_pdf(
    consignment_id: int,
    mrn: str,
    _: ViewerUser,
    db: DbDep,
    download: bool = False,
) -> FileResponse:
    """Auth-gated stream of the EAD PDF.

    Looks up the customs row by (consignment_id, mrn) and resolves
    ``pdf_ref`` against ``CUSTOMS_ROOT`` (default ``/data/customs``).
    Refuses any resolved path that escapes the customs root — defence
    against tampered ``pdf_ref`` values.

    Defaults to ``Content-Disposition: inline`` so the popup iframe can
    render the PDF in-place via the browser's built-in viewer. Pass
    ``?download=1`` to force ``attachment`` (used by the modal's
    Download button).
    """
    if not _MRN_RE.match(mrn):
        raise HTTPException(status_code=400, detail="Invalid MRN format")
    # Verify parent consignment is alive.
    await _get_or_404(db, consignment_id)

    row = (
        await db.execute(
            select(ConsignmentPosCustoms).where(
                ConsignmentPosCustoms.consignment_id == consignment_id,
                ConsignmentPosCustoms.mrn == mrn,
                ConsignmentPosCustoms.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None or not row.pdf_ref:
        raise HTTPException(status_code=404, detail="EAD not found for this MRN")

    root = _CUSTOMS_ROOT.resolve()
    candidate = (root / row.pdf_ref).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="pdf_ref escapes customs root") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="EAD PDF missing on disk")

    return FileResponse(
        path=candidate,
        media_type="application/pdf",
        filename=f"DMS_EXPORT_{mrn}.pdf",
        content_disposition_type="attachment" if download else "inline",
    )


# ---------------------------------------------------------------------------
# Commercial invoice sub-resource — PDF streaming
# ---------------------------------------------------------------------------


_INVOICES_ROOT = Path(os.environ.get("INVOICES_ROOT", "/data/invoices"))
# OisteBio commercial invoice number to Crown Oil Ltd.
# Format: ``OIS-INV<digits>`` (e.g. ``OIS-INV250023``).
_INVOICE_RE = re.compile(r"^OIS-INV\d{4,12}$")


@router.get("/{consignment_id}/invoices/{invoice_no}.pdf")
async def stream_invoice_pdf(
    consignment_id: int,
    invoice_no: str,
    _: ViewerUser,
    db: DbDep,
    download: bool = False,
) -> FileResponse:
    """Auth-gated stream of the OisteBio→Crown Oil commercial invoice.

    Looks up the customs row by (consignment_id, invoice_no) and
    resolves ``invoice_pdf_ref`` against ``INVOICES_ROOT`` (default
    ``/data/invoices``).  Refuses any resolved path that escapes the
    invoices root.

    Defaults to ``Content-Disposition: inline`` so the popup iframe can
    render the PDF in-place. Pass ``?download=1`` to force
    ``attachment`` (used by the modal's Download button).
    """
    if not _INVOICE_RE.match(invoice_no):
        raise HTTPException(status_code=400, detail="Invalid invoice number")
    await _get_or_404(db, consignment_id)

    row = (
        await db.execute(
            select(ConsignmentPosCustoms).where(
                ConsignmentPosCustoms.consignment_id == consignment_id,
                ConsignmentPosCustoms.invoice_no == invoice_no,
                ConsignmentPosCustoms.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None or not row.invoice_pdf_ref:
        raise HTTPException(
            status_code=404, detail="Invoice not found for this number"
        )

    root = _INVOICES_ROOT.resolve()
    candidate = (root / row.invoice_pdf_ref).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="invoice_pdf_ref escapes invoices root"
        ) from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Invoice PDF missing on disk")

    return FileResponse(
        path=candidate,
        media_type="application/pdf",
        filename=f"INV_{invoice_no}.pdf",
        content_disposition_type="attachment" if download else "inline",
    )


# ---------------------------------------------------------------------------
# Ocean BL sub-resource — PDF streaming
# ---------------------------------------------------------------------------


_BL_OCEAN_ROOT = Path(os.environ.get("BL_OCEAN_ROOT", "/data/bl_ocean"))
_POS_ROOT = Path(os.environ.get("POS_ROOT", "/data/pos_documents"))
_DELIVERY_UK_ROOT = Path(os.environ.get("DELIVERY_UK_ROOT", "/data/delivery_uk"))
# Ocean BL number prefix is the SCAC code (4 uppercase letters, e.g. CMDU
# for CMA-CGM, MAEU for Maersk, MEDU for MSC, HLCU for Hapag-Lloyd)
# followed by 6–12 digits. Strict anchor keeps URLs safe from path-traversal.
_BL_OCEAN_RE = re.compile(r"^[A-Z]{4}\d{6,12}$")


@router.get("/{consignment_id}/bl/{bl_no}.pdf")
async def stream_bl_ocean_pdf(
    consignment_id: int,
    bl_no: str,
    _: ViewerUser,
    db: DbDep,
    download: bool = False,
) -> FileResponse:
    """Auth-gated stream of the Ocean BL PDF.

    Looks up the ``shipment_leg`` row by
    ``(consignment_id, document_ref=bl_no, leg_type='bl_ocean')`` and
    resolves ``pdf_ref`` against ``BL_OCEAN_ROOT`` (default
    ``/data/bl_ocean``).  Refuses any resolved path that escapes the
    BL-ocean root — defence against tampered ``pdf_ref`` values.

    Defaults to ``Content-Disposition: inline`` so the popup iframe can
    render the PDF in-place via the browser's built-in viewer. Pass
    ``?download=1`` to force ``attachment`` (used by the modal's
    Download button).
    """
    if not _BL_OCEAN_RE.match(bl_no):
        raise HTTPException(status_code=400, detail="Invalid BL number format")
    await _get_or_404(db, consignment_id)

    row = (
        await db.execute(
            select(ShipmentLeg).where(
                ShipmentLeg.consignment_id == consignment_id,
                ShipmentLeg.document_ref == bl_no,
                ShipmentLeg.leg_type == "bl_ocean",
                ShipmentLeg.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None or not row.pdf_ref:
        raise HTTPException(status_code=404, detail="Ocean BL not found for this number")

    root = _BL_OCEAN_ROOT.resolve()
    candidate = (root / row.pdf_ref).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="pdf_ref escapes bl_ocean root"
        ) from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="BL PDF missing on disk")

    return FileResponse(
        path=candidate,
        media_type="application/pdf",
        filename=f"BL_{bl_no}.pdf",
        content_disposition_type="attachment" if download else "inline",
    )


# ---------------------------------------------------------------------------
# PoS sub-resource
# ---------------------------------------------------------------------------


@router.post(
    "/{consignment_id}/pos",
    response_model=ConsignmentPosOut,
    status_code=status.HTTP_201_CREATED,
)
async def attach_pos(
    consignment_id: int,
    body: ConsignmentPosCreate,
    user: OperatorUser,
    db: DbDep,
) -> ConsignmentPos:
    """Attach a PoS document to a consignment. Operator+ required.

    No audit written for association rows (noise-reduction decision).
    """
    # Verify parent exists and is not deleted
    await _get_or_404(db, consignment_id)

    # Composite PK is (consignment_id, pos_number). If an existing row is
    # soft-deleted, revive it; otherwise INSERT. Active duplicate → 409.
    existing = (
        await db.execute(
            select(ConsignmentPos).where(
                ConsignmentPos.consignment_id == consignment_id,
                ConsignmentPos.pos_number == body.pos_number,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="pos_number already exists for this consignment",
            )
        # Revive: clear deleted_at, refresh payload from body (ersv_outbound_no
        # is intentionally NOT cleared — preserve historical allocation).
        existing.deleted_at = None
        for k, v in body.model_dump(exclude={"pos_number"}).items():
            setattr(existing, k, v)
        await db.commit()
        await db.refresh(existing)
        return existing

    obj = ConsignmentPos(
        consignment_id=consignment_id,
        **body.model_dump(),
    )
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="pos_number already exists for this consignment",
        ) from exc
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete(
    "/{consignment_id}/pos/{pos_number}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_pos(
    consignment_id: int,
    pos_number: str,
    user: AdminUser,
    db: DbDep,
) -> None:
    """Soft-delete a PoS association (sets deleted_at).

    Since 0022 consignment_pos carries an outbound eRSV number under a partial
    UNIQUE index (active rows only). Soft-deleting frees the number for reuse
    while preserving the historical row. No audit written (association row).
    """
    result = await db.execute(
        select(ConsignmentPos).where(
            ConsignmentPos.consignment_id == consignment_id,
            ConsignmentPos.pos_number == pos_number,
            ConsignmentPos.deleted_at.is_(None),
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PoS not found for this consignment"
        )
    obj.deleted_at = datetime.now(UTC)
    await db.commit()


@router.get("/{consignment_id}/pos/{pos_number}.pdf")
async def stream_pos_pdf(
    consignment_id: int,
    pos_number: str,
    _: ViewerUser,
    db: DbDep,
    download: bool = False,
) -> FileResponse:
    """Auth-gated stream of the Proof-of-Sustainability PDF.

    Looks up the ``consignment_pos`` row by ``(consignment_id, pos_number)``
    and resolves ``pdf_ref`` against ``POS_ROOT`` (default
    ``/data/pos_documents``). Refuses any resolved path that escapes the
    PoS root — defence against tampered ``pdf_ref`` values (which still
    carry historical ``gdrive:…`` prefixes until the G6 backfill runs).

    Defaults to ``Content-Disposition: inline`` so the popup iframe can
    render the PDF via the browser's built-in viewer. Pass
    ``?download=1`` to force ``attachment``.
    """
    await _get_or_404(db, consignment_id)

    row = (
        await db.execute(
            select(ConsignmentPos).where(
                ConsignmentPos.consignment_id == consignment_id,
                ConsignmentPos.pos_number == pos_number,
                ConsignmentPos.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None or not row.pdf_ref:
        raise HTTPException(status_code=404, detail="PoS not found for this consignment")

    # Refuse historical Drive refs explicitly — surfaces the migration
    # state instead of silently 404-ing on a missing local file.
    if row.pdf_ref.startswith("gdrive:"):
        raise HTTPException(
            status_code=409,
            detail="PoS pdf_ref still points at Drive — run scripts/backfill_pos_pdf_ref.py",
        )

    root = _POS_ROOT.resolve()
    candidate = (root / row.pdf_ref).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="pdf_ref escapes pos_documents root"
        ) from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="PoS PDF missing on disk")

    safe_no = re.sub(r"[^A-Za-z0-9_.-]+", "_", pos_number)
    return FileResponse(
        path=candidate,
        media_type="application/pdf",
        filename=f"PoS_{safe_no}.pdf",
        content_disposition_type="attachment" if download else "inline",
    )


# ---------------------------------------------------------------------------
# Delivery-UK bundle sub-resource — PDF streaming
# ---------------------------------------------------------------------------


@router.get("/{consignment_id}/delivery-uk.pdf")
async def stream_delivery_uk_pdf(
    consignment_id: int,
    _: ViewerUser,
    db: DbDep,
    download: bool = False,
) -> FileResponse:
    """Auth-gated stream of the JLY commercial-invoice bundle.

    Looks up the ``shipment_leg`` row by
    ``(consignment_id, leg_type='delivery_uk', deleted_at IS NULL)`` and
    resolves ``pdf_ref`` against ``DELIVERY_UK_ROOT`` (default
    ``/data/delivery_uk``). Refuses any resolved path that escapes the
    delivery-uk root — defence against tampered ``pdf_ref`` values.

    Defaults to ``Content-Disposition: inline`` so the popup iframe can
    render the bundle in-place. Pass ``?download=1`` to force
    ``attachment`` (used by the modal's Download button).
    """
    await _get_or_404(db, consignment_id)

    row = (
        await db.execute(
            select(ShipmentLeg).where(
                ShipmentLeg.consignment_id == consignment_id,
                ShipmentLeg.leg_type == "delivery_uk",
                ShipmentLeg.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None or not row.pdf_ref:
        raise HTTPException(
            status_code=404, detail="Delivery-UK bundle not found for this consignment"
        )

    root = _DELIVERY_UK_ROOT.resolve()
    candidate = (root / row.pdf_ref).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="pdf_ref escapes delivery_uk root"
        ) from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Delivery-UK PDF missing on disk")

    safe_ref = re.sub(r"[^A-Za-z0-9_.-]+", "_", row.document_ref or "delivery-uk")
    return FileResponse(
        path=candidate,
        media_type="application/pdf",
        filename=f"{safe_ref}.pdf",
        content_disposition_type="attachment" if download else "inline",
    )


# ---------------------------------------------------------------------------
# Production link sub-resource
# ---------------------------------------------------------------------------


@router.post(
    "/{consignment_id}/production-links",
    response_model=ConsignmentProductionLinkOut,
    status_code=status.HTTP_201_CREATED,
)
async def attach_production_link(
    consignment_id: int,
    body: ConsignmentProductionLinkCreate,
    user: OperatorUser,
    db: DbDep,
) -> ConsignmentProductionLink:
    """Link a production day to this consignment with kg_allocated. Operator+ required.

    No audit written for association rows (noise-reduction decision).
    """
    await _get_or_404(db, consignment_id)
    obj = ConsignmentProductionLink(
        consignment_id=consignment_id,
        **body.model_dump(),
    )
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Production link already exists for this consignment + prod_date",
        ) from exc
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete(
    "/{consignment_id}/production-links/{prod_date}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_production_link(
    consignment_id: int,
    prod_date: date,
    user: AdminUser,
    db: DbDep,
) -> None:
    """Hard-delete a production-link row. No deleted_at on this table — hard delete is correct.

    No audit written for association rows (noise-reduction decision).
    """
    result = await db.execute(
        select(ConsignmentProductionLink).where(
            ConsignmentProductionLink.consignment_id == consignment_id,
            ConsignmentProductionLink.prod_date == prod_date,
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production link not found for this consignment + prod_date",
        )
    await db.delete(obj)
    await db.commit()
