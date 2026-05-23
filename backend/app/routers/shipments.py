"""Router: shipment_leg + shipment_unit.

Auth: reads require viewer+; POST/PATCH require operator+; DELETE on legs requires admin.
Audit: insert / update / soft_delete written for shipment_leg (not for shipment_unit —
  noise-reduction decision; documented here intentionally).
Soft delete: legs only — set deleted_at = NOW(). ShipmentUnit has no deleted_at, so
  DELETE /shipments/units/{id} is a hard delete.

Status auto-advance (Q8 locked):
  When a new shipment_leg with leg_type='delivery_uk' is created, the parent
  consignment's status is automatically advanced to 'delivered_uk' if it is
  not already 'delivered_uk' or 'closed'. This check runs after the leg insert
  commits (within the same transaction).

Business rules validated before DB insert:
  - kg_in >= kg_out (pre-validated for a clear 422; DB CHECK is also present)
  - utb_transload: kg_stock_residual must be set and kg_in == kg_out + kg_stock_residual
  - seq unique per consignment (409 on IntegrityError from unique constraint)
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AdminUser, OperatorUser, ViewerUser
from app.db.session import get_db
from app.models.consignment import Consignment
from app.models.shipment_leg import ShipmentLeg
from app.models.shipment_unit import ShipmentUnit
from app.schemas.logistics import (
    ShipmentLegCreate,
    ShipmentLegDetail,
    ShipmentLegOut,
    ShipmentLegUpdate,
    ShipmentUnitCreate,
    ShipmentUnitOut,
    ShipmentUnitUpdate,
)
from app.services.audit import model_snapshot, write_audit

router = APIRouter(prefix="/shipments", tags=["shipments"])
DbDep = Annotated[AsyncSession, Depends(get_db)]

_LEG_TABLE = "shipment_leg"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_leg_or_404(
    db: AsyncSession,
    leg_id: int,
    *,
    include_deleted: bool = False,
) -> ShipmentLeg:
    stmt = select(ShipmentLeg).where(ShipmentLeg.id == leg_id)
    if not include_deleted:
        stmt = stmt.where(ShipmentLeg.deleted_at.is_(None))
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ShipmentLeg not found"
        )
    return obj


async def _get_unit_or_404(db: AsyncSession, unit_id: int) -> ShipmentUnit:
    result = await db.execute(select(ShipmentUnit).where(ShipmentUnit.id == unit_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ShipmentUnit not found"
        )
    return obj


def _validate_leg_mass_balance(body: ShipmentLegCreate) -> None:
    """Pre-validate mass-balance rules before hitting the DB.

    Raises HTTP 422 with a descriptive message so the client gets a clear error
    rather than a cryptic DB check-constraint violation.
    """
    if body.kg_in < body.kg_out:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"kg_in ({body.kg_in}) must be >= kg_out ({body.kg_out}): "
                "mass cannot be created in a shipment leg"
            ),
        )
    if body.leg_type.value == "utb_transload":
        if body.kg_stock_residual is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "kg_stock_residual is required for leg_type='utb_transload': "
                    "the UTB residual stock must be explicitly accounted for"
                ),
            )
        expected_out = body.kg_in - body.kg_stock_residual
        # Allow small float drift; we use Decimal so compare directly
        if body.kg_out != expected_out:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"For utb_transload: kg_in ({body.kg_in}) must equal "
                    f"kg_out ({body.kg_out}) + kg_stock_residual ({body.kg_stock_residual}). "
                    f"Expected kg_out = {expected_out}"
                ),
            )


async def _maybe_advance_consignment_status(db: AsyncSession, consignment_id: int) -> None:
    """Auto-advance consignment status to 'delivered_uk' when a delivery_uk leg is created.

    Called after inserting a leg with leg_type='delivery_uk'. The consignment
    status is only updated if it is not already 'delivered_uk' or 'closed'.
    This implements the Q8 locked decision: auto-update via last leg, plus
    manual override via PATCH /consignments/{id} (admin only for status field).
    """
    result = await db.execute(
        select(Consignment).where(Consignment.id == consignment_id)
    )
    consignment = result.scalar_one_or_none()
    if consignment is None:
        return
    if consignment.status not in ("delivered_uk", "closed"):
        consignment.status = "delivered_uk"
        await db.flush()


# ---------------------------------------------------------------------------
# Shipment Legs
# ---------------------------------------------------------------------------


@router.get("/legs", response_model=list[ShipmentLegOut])
async def list_legs(
    _: ViewerUser,
    db: DbDep,
    consignment_id: int | None = Query(None),
    include_deleted: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
) -> list[ShipmentLeg]:
    """List shipment legs, optionally filtered by consignment_id."""
    stmt = select(ShipmentLeg)
    if not include_deleted:
        stmt = stmt.where(ShipmentLeg.deleted_at.is_(None))
    if consignment_id is not None:
        stmt = stmt.where(ShipmentLeg.consignment_id == consignment_id)
    stmt = stmt.order_by(ShipmentLeg.consignment_id, ShipmentLeg.seq).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/legs", response_model=ShipmentLegOut, status_code=status.HTTP_201_CREATED)
async def create_leg(
    body: ShipmentLegCreate,
    user: OperatorUser,
    db: DbDep,
) -> ShipmentLeg:
    """Create a shipment leg. Operator+ required.

    Validates:
      - kg_in >= kg_out (422 if violated)
      - utb_transload: kg_stock_residual required; kg_in == kg_out + kg_stock_residual (422)
      - seq unique per consignment (409 on conflict)

    Auto-advances parent consignment status to 'delivered_uk' when leg_type='delivery_uk'.
    """
    _validate_leg_mass_balance(body)

    obj = ShipmentLeg(**body.model_dump())
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Conflict inserting leg: seq may already exist for this consignment, "
                "or FK (consignment_id / operator_certificate_id) is invalid"
            ),
        ) from exc
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_LEG_TABLE,
        record_id=obj.id,
        action="insert",
        old_values=None,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )

    # Q8: auto-advance consignment to delivered_uk when delivery_uk leg is created
    if body.leg_type.value == "delivery_uk":
        await _maybe_advance_consignment_status(db, body.consignment_id)

    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/legs/{leg_id}", response_model=ShipmentLegDetail)
async def get_leg_detail(
    leg_id: int,
    _: ViewerUser,
    db: DbDep,
) -> ShipmentLegDetail:
    """Return a single leg with its shipment_unit children."""
    leg = await _get_leg_or_404(db, leg_id)
    units_result = await db.execute(
        select(ShipmentUnit).where(ShipmentUnit.leg_id == leg_id).order_by(ShipmentUnit.id)
    )
    units = [ShipmentUnitOut.model_validate(u) for u in units_result.scalars().all()]
    return ShipmentLegDetail(
        **{k: getattr(leg, k) for k in ShipmentLegDetail.model_fields if k != "units"},
        units=units,
    )


@router.patch("/legs/{leg_id}", response_model=ShipmentLegOut)
async def update_leg(
    leg_id: int,
    body: ShipmentLegUpdate,
    user: OperatorUser,
    db: DbDep,
) -> ShipmentLeg:
    """Partial update on a leg. Operator+ required."""
    obj = await _get_leg_or_404(db, leg_id)
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
            detail="Conflict updating leg: seq conflict or FK invalid",
        ) from exc
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_LEG_TABLE,
        record_id=obj.id,
        action="update",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/legs/{leg_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_leg(
    leg_id: int,
    user: AdminUser,
    db: DbDep,
) -> None:
    """Soft delete a leg (sets deleted_at). Admin only. DB row is never removed."""
    obj = await _get_leg_or_404(db, leg_id)
    old = model_snapshot(obj)
    obj.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    await db.refresh(obj)
    await write_audit(
        db,
        table_name=_LEG_TABLE,
        record_id=obj.id,
        action="soft_delete",
        old_values=old,
        new_values=model_snapshot(obj),
        changed_by=user.id,
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Shipment Units
# ---------------------------------------------------------------------------


@router.get("/legs/{leg_id}/units", response_model=list[ShipmentUnitOut])
async def list_units(
    leg_id: int,
    _: ViewerUser,
    db: DbDep,
) -> list[ShipmentUnit]:
    """List all shipment units (containers/tanks) for a given leg."""
    # Confirm leg exists
    await _get_leg_or_404(db, leg_id)
    result = await db.execute(
        select(ShipmentUnit).where(ShipmentUnit.leg_id == leg_id).order_by(ShipmentUnit.id)
    )
    return list(result.scalars().all())


@router.post(
    "/legs/{leg_id}/units",
    response_model=ShipmentUnitOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_unit(
    leg_id: int,
    body: ShipmentUnitCreate,
    user: OperatorUser,
    db: DbDep,
) -> ShipmentUnit:
    """Add a container/tank unit to a leg. Operator+ required.

    No audit written for shipment_unit (noise-reduction decision).
    """
    await _get_leg_or_404(db, leg_id)
    obj = ShipmentUnit(leg_id=leg_id, **body.model_dump())
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict inserting unit: FK invalid or constraint violated",
        ) from exc
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/units/{unit_id}", response_model=ShipmentUnitOut)
async def update_unit(
    unit_id: int,
    body: ShipmentUnitUpdate,
    user: OperatorUser,
    db: DbDep,
) -> ShipmentUnit:
    """Partial update on a shipment unit. Operator+ required.

    No audit written for shipment_unit (noise-reduction decision).
    """
    obj = await _get_unit_or_404(db, unit_id)
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
            detail="Conflict updating unit",
        ) from exc
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: int,
    user: AdminUser,
    db: DbDep,
) -> None:
    """Hard-delete a shipment unit. ShipmentUnit has no deleted_at column — hard delete is correct.

    No audit written for shipment_unit (noise-reduction decision).
    """
    obj = await _get_unit_or_404(db, unit_id)
    await db.delete(obj)
    await db.commit()
