"""Router: consignments + consignment_pos + consignment_production_link.

Auth: reads require viewer+; POST/PATCH require operator+; DELETE requires admin.
Audit: insert / update / soft_delete written to audit_log.
Soft delete: DELETE /consignments/{id} sets deleted_at = NOW().
No audit on consignment_pos / consignment_production_link (association rows —
  noise-reduction decision; documented here intentionally).
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser, OperatorUser, ViewerUser
from app.db.session import get_db
from app.models.consignment import Consignment
from app.models.consignment_pos import ConsignmentPos
from app.models.consignment_production_link import ConsignmentProductionLink
from app.models.off_taker import OffTaker
from app.models.shipment_leg import ShipmentLeg
from app.models.shipment_unit import ShipmentUnit
from app.schemas.logistics import (
    ConsignmentCreate,
    ConsignmentDetail,
    ConsignmentOut,
    ConsignmentPosCreate,
    ConsignmentPosOut,
    ConsignmentProductionLinkCreate,
    ConsignmentProductionLinkOut,
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


@router.get("", response_model=list[ConsignmentOut])
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
) -> list[Consignment]:
    """List consignments with optional filters on off_taker, status, and production date range."""
    stmt = select(Consignment)
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
    return list(result.scalars().all())


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

    base = ConsignmentOut.model_validate(obj)
    return ConsignmentDetail(
        **base.model_dump(),
        off_taker=off_taker_row,
        legs=leg_details,
        pos=pos_list,
        production_links=links,
    )


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
